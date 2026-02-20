"""Webhook dispatcher and delivery system"""

import asyncio
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta
from uuid import UUID, uuid4

import httpx
from sqlalchemy.orm import Session

from app.modules.webhooks.domain.entities import (
    DeliveryStatus,
    WebhookDeliveryAttempt,
    WebhookEndpoint,
    WebhookEvent,
    WebhookEventType,
    WebhookPayload,
)

logger = logging.getLogger(__name__)


class WebhookDispatcher:
    """Main webhook dispatcher and delivery system"""

    def __init__(self, db: Session):
        self.db = db
        self.max_retries = 5
        self.backoff_base = 2  # Exponential backoff: 2^attempt

    def trigger(
        self,
        event_type: WebhookEventType,
        resource_type: str,
        resource_id: str,
        data: dict,
        tenant_id: str,
    ) -> UUID:
        """
        Trigger a webhook event

        Args:
            event_type: Type of event
            resource_type: Type of resource (invoice, sales_order, etc.)
            resource_id: ID of the resource
            data: Event data payload
            tenant_id: Tenant ID

        Returns:
            Event ID
        """
        event_id = uuid4()

        try:
            # Create event
            _event = WebhookEvent(
                id=event_id,
                webhook_id=uuid4(),  # Will be set per endpoint
                tenant_id=tenant_id,
                event_type=event_type,
                resource_type=resource_type,
                resource_id=resource_id,
                payload=data,
                timestamp=datetime.now(),
                delivery_status=DeliveryStatus.PENDING,
            )

            logger.info(f"Webhook event triggered: {event_type.value} for {resource_type}")
            return event_id

        except Exception as e:
            logger.error(f"Failed to trigger webhook: {e}")
            raise

    async def dispatch(
        self,
        event: WebhookEvent,
        endpoints: list[WebhookEndpoint],
    ) -> dict[UUID, DeliveryStatus]:
        """
        Dispatch event to all matching endpoints

        Args:
            event: Webhook event
            endpoints: List of webhook endpoints to dispatch to

        Returns:
            Dictionary mapping endpoint_id to delivery_status
        """
        results = {}

        # Create payload
        payload = WebhookPayload(
            id=str(event.id),
            timestamp=event.timestamp,
            event=event.event_type,
            data=event.payload,
            tenant_id=event.tenant_id,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
        )

        # Dispatch to each endpoint
        tasks = []
        for endpoint in endpoints:
            if not endpoint.active or endpoint.status != "active":
                continue

            if event.event_type not in endpoint.events:
                continue

            task = self._deliver_to_endpoint(endpoint, payload)
            tasks.append((endpoint.id, task))

        # Execute all deliveries concurrently
        if tasks:
            for endpoint_id, task in tasks:
                try:
                    status = await task
                    results[endpoint_id] = status
                except Exception as e:
                    logger.error(f"Dispatch failed for endpoint {endpoint_id}: {e}")
                    results[endpoint_id] = DeliveryStatus.FAILED

        return results

    async def _deliver_to_endpoint(
        self, endpoint: WebhookEndpoint, payload: WebhookPayload
    ) -> DeliveryStatus:
        """
        Deliver webhook to a single endpoint

        Args:
            endpoint: Webhook endpoint
            payload: Payload to send

        Returns:
            Delivery status
        """
        payload_dict = payload.to_dict()
        signature = self._generate_signature(endpoint.secret, payload_dict)

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "GestiqCloud-Webhooks/1.0",
            "X-Webhook-Signature": signature,
            "X-Webhook-ID": payload.id,
            "X-Webhook-Timestamp": payload.timestamp.isoformat(),
        }

        # Add custom headers
        if endpoint.headers:
            headers.update(endpoint.headers)

        attempt = 0
        last_error = None

        while attempt < endpoint.max_retries:
            attempt += 1

            try:
                async with httpx.AsyncClient(timeout=endpoint.timeout_seconds) as client:
                    response = await client.post(
                        endpoint.url,
                        json=payload_dict,
                        headers=headers,
                    )

                    # Log attempt
                    attempt_record = WebhookDeliveryAttempt(
                        id=uuid4(),
                        webhook_id=endpoint.id,
                        event_id=payload.id,
                        attempt_number=attempt,
                        status=(
                            DeliveryStatus.DELIVERED
                            if response.status_code < 400
                            else DeliveryStatus.FAILED
                        ),
                        http_status_code=response.status_code,
                        response_body=response.text[:1000],  # Store first 1000 chars
                        request_timestamp=datetime.now(),
                        response_timestamp=datetime.now(),
                    )

                    logger.info(
                        f"Webhook delivery attempt {attempt} to {endpoint.url}: "
                        f"HTTP {response.status_code}"
                    )

                    # Success (2xx or 3xx)
                    if response.status_code < 400:
                        return DeliveryStatus.DELIVERED

                    # Failure - will retry
                    if response.status_code < 500:
                        # 4xx errors usually don't warrant retry
                        return DeliveryStatus.FAILED

                    last_error = f"HTTP {response.status_code}"

            except httpx.TimeoutException:
                last_error = "Request timeout"
                logger.warning(f"Webhook delivery timeout to {endpoint.url} (attempt {attempt})")

            except httpx.RequestError as e:
                last_error = str(e)
                logger.warning(
                    f"Webhook delivery failed to {endpoint.url}: {e} (attempt {attempt})"
                )

            except Exception as e:
                last_error = str(e)
                logger.error(f"Unexpected error delivering webhook: {e}")

            # Calculate next retry time (exponential backoff)
            if attempt < endpoint.max_retries:
                backoff_seconds = self.backoff_base**attempt
                next_retry = datetime.now() + timedelta(seconds=backoff_seconds)

                attempt_record.status = DeliveryStatus.RETRYING
                attempt_record.next_retry_at = next_retry

                logger.info(f"Scheduling retry for {endpoint.url} in {backoff_seconds}s")

                # Wait before retrying
                await asyncio.sleep(backoff_seconds)

        # All retries exhausted
        logger.error(
            f"Webhook delivery failed after {endpoint.max_retries} attempts to {endpoint.url}. "
            f"Last error: {last_error}"
        )
        return DeliveryStatus.ABANDONED

    def _generate_signature(self, secret: str, payload: dict) -> str:
        """
        Generate HMAC signature for webhook payload

        Args:
            secret: Webhook secret
            payload: Payload dictionary

        Returns:
            Hex signature
        """
        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        signature = hmac.new(
            secret.encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

        return f"sha256={signature}"

    @staticmethod
    def verify_signature(secret: str, payload: dict, signature: str) -> bool:
        """
        Verify webhook signature (for receiving end)

        Args:
            secret: Webhook secret
            payload: Payload dictionary
            signature: Signature to verify

        Returns:
            True if signature is valid
        """
        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        expected_signature = hmac.new(
            secret.encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

        normalized = signature.strip()
        if normalized.lower().startswith("sha256="):
            normalized = normalized.split("=", 1)[1]

        return hmac.compare_digest(normalized, expected_signature)


class WebhookRegistry:
    """Registry of webhook event triggers"""

    def __init__(self):
        self.triggers = {}

    def register_trigger(self, event_type: WebhookEventType, resource_type: str):
        """Register a trigger point"""
        key = f"{resource_type}:{event_type.value}"
        self.triggers[key] = True

    def is_event_supported(self, event_type: WebhookEventType, resource_type: str) -> bool:
        """Check if event is supported"""
        key = f"{resource_type}:{event_type.value}"
        return key in self.triggers


# Global registry
webhook_registry = WebhookRegistry()

# Register default triggers
webhook_registry.register_trigger(WebhookEventType.INVOICE_CREATED, "invoice")
webhook_registry.register_trigger(WebhookEventType.INVOICE_SENT, "invoice")
webhook_registry.register_trigger(WebhookEventType.INVOICE_AUTHORIZED, "invoice")
webhook_registry.register_trigger(WebhookEventType.INVOICE_REJECTED, "invoice")
webhook_registry.register_trigger(WebhookEventType.SALES_ORDER_CREATED, "sales_order")
webhook_registry.register_trigger(WebhookEventType.SALES_ORDER_CONFIRMED, "sales_order")
webhook_registry.register_trigger(WebhookEventType.PAYMENT_RECEIVED, "payment")
webhook_registry.register_trigger(WebhookEventType.CUSTOMER_CREATED, "customer")
webhook_registry.register_trigger(WebhookEventType.CUSTOMER_UPDATED, "customer")
