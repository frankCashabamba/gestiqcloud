"""
Webhook triggers for sales module

Handles sending webhook events when sales orders are created, confirmed, or cancelled.
Integrates with the webhooks module for secure, async delivery.
"""

import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.webhooks.utils import WebhookFormatter

logger = logging.getLogger(__name__)


class SalesOrderWebhookService:
    """Service for triggering webhooks from sales module"""

    def __init__(self, db: Session):
        self.db = db

    def trigger_sales_order_created(
        self,
        tenant_id: UUID,
        order_id: str,
        order_number: str,
        customer_id: str | None = None,
        customer_name: str | None = None,
        amount: float = 0,
        currency: str = "USD",
        items_count: int = 0,
    ) -> bool:
        """
        Trigger webhook when sales order is created

        Args:
            tenant_id: Tenant UUID
            order_id: Order unique identifier
            order_number: Human-readable order number
            customer_id: Customer ID if available
            customer_name: Customer name
            amount: Order total amount
            currency: Currency code (USD, EUR, etc.)
            items_count: Number of items in order

        Returns:
            True if webhook was enqueued, False otherwise
        """
        try:
            payload = WebhookFormatter.format_event_payload(
                event="sales_order.created",
                resource_type="sales_order",
                resource_id=order_id,
                data={
                    "order_id": order_id,
                    "order_number": order_number,
                    "customer_id": customer_id,
                    "customer_name": customer_name,
                    "amount": str(amount),
                    "currency": currency,
                    "items_count": items_count,
                    "status": "draft",
                    "created_at": datetime.utcnow().isoformat(),
                },
                tenant_id=str(tenant_id),
            )
            result = self._enqueue_delivery(tenant_id, "sales_order.created", payload)
            if result:
                logger.info(f"Enqueued webhook for sales_order.created: {order_id}")
            return result
        except Exception as e:
            logger.error(f"Error triggering sales_order.created webhook: {e}", exc_info=True)
            return False

    def trigger_sales_order_confirmed(
        self,
        tenant_id: UUID,
        order_id: str,
        order_number: str,
        customer_id: str | None = None,
        customer_name: str | None = None,
        amount: float = 0,
        currency: str = "USD",
    ) -> bool:
        """
        Trigger webhook when sales order is confirmed

        Args:
            tenant_id: Tenant UUID
            order_id: Order unique identifier
            order_number: Human-readable order number
            customer_id: Customer ID if available
            customer_name: Customer name
            amount: Order total amount
            currency: Currency code

        Returns:
            True if webhook was enqueued, False otherwise
        """
        try:
            payload = WebhookFormatter.format_event_payload(
                event="sales_order.confirmed",
                resource_type="sales_order",
                resource_id=order_id,
                data={
                    "order_id": order_id,
                    "order_number": order_number,
                    "customer_id": customer_id,
                    "customer_name": customer_name,
                    "amount": str(amount),
                    "currency": currency,
                    "status": "confirmed",
                    "confirmed_at": datetime.utcnow().isoformat(),
                },
                tenant_id=str(tenant_id),
            )
            result = self._enqueue_delivery(tenant_id, "sales_order.confirmed", payload)
            if result:
                logger.info(f"Enqueued webhook for sales_order.confirmed: {order_id}")
            return result
        except Exception as e:
            logger.error(f"Error triggering sales_order.confirmed webhook: {e}", exc_info=True)
            return False

    def trigger_sales_order_cancelled(
        self,
        tenant_id: UUID,
        order_id: str,
        order_number: str,
        reason: str | None = None,
    ) -> bool:
        """
        Trigger webhook when sales order is cancelled

        Args:
            tenant_id: Tenant UUID
            order_id: Order unique identifier
            order_number: Human-readable order number
            reason: Cancellation reason

        Returns:
            True if webhook was enqueued, False otherwise
        """
        try:
            payload = WebhookFormatter.format_event_payload(
                event="sales_order.cancelled",
                resource_type="sales_order",
                resource_id=order_id,
                data={
                    "order_id": order_id,
                    "order_number": order_number,
                    "reason": reason,
                    "status": "cancelled",
                    "cancelled_at": datetime.utcnow().isoformat(),
                },
                tenant_id=str(tenant_id),
            )
            result = self._enqueue_delivery(tenant_id, "sales_order.cancelled", payload)
            if result:
                logger.info(f"Enqueued webhook for sales_order.cancelled: {order_id}")
            return result
        except Exception as e:
            logger.error(f"Error triggering sales_order.cancelled webhook: {e}", exc_info=True)
            return False

    def _enqueue_delivery(self, tenant_id: UUID, event: str, payload: dict[str, Any]) -> bool:
        """
        Internal method to enqueue webhook delivery for all active subscriptions

        Args:
            tenant_id: Tenant UUID
            event: Event name (e.g., "sales_order.created")
            payload: Event payload data

        Returns:
            True if at least one delivery was queued, False if no subscriptions found
        """
        try:
            tenant_id_str = str(tenant_id)

            # Check if there are active subscriptions for this event
            result = self.db.execute(
                text("""
                    SELECT COUNT(*) FROM webhook_subscriptions
                    WHERE tenant_id = CAST(:tid AS uuid) AND event = :event AND active = true
                    """),
                {"tid": tenant_id_str, "event": event},
            ).scalar()

            if not result:
                logger.debug(f"No active subscriptions for {event}")
                return False

            # Get all subscriptions for this event
            subs = self.db.execute(
                text("""
                    SELECT url, secret FROM webhook_subscriptions
                    WHERE tenant_id = CAST(:tid AS uuid) AND event = :event AND active = true
                    """),
                {"tid": tenant_id_str, "event": event},
            ).fetchall()

            # Create delivery records
            payload_json = json.dumps(payload, ensure_ascii=False)
            delivery_count = 0

            for url, secret in subs:
                self.db.execute(
                    text("""
                        INSERT INTO webhook_deliveries(
                            tenant_id, event, payload, target_url, secret, status
                        )
                        VALUES (CAST(:tid AS uuid), :event, :payload::jsonb, :url, :secret, 'PENDING')
                        """),
                    {
                        "tid": tenant_id_str,
                        "event": event,
                        "payload": payload_json,
                        "url": url,
                        "secret": secret,
                    },
                )
                delivery_count += 1

            self.db.commit()
            logger.info(
                f"Enqueued {delivery_count} webhook deliveries for {event} "
                f"(tenant: {tenant_id_str})"
            )
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error enqueueing webhook delivery: {e}", exc_info=True)
            return False
