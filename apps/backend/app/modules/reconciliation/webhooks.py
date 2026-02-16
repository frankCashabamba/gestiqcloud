"""
Webhook triggers for reconciliation/payments module

Handles sending webhook events when payments are received or failed.
Integrates with the webhooks module for secure, async delivery.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.webhooks.utils import WebhookFormatter

logger = logging.getLogger(__name__)


class PaymentWebhookService:
    """Service for triggering webhooks from payments module"""

    def __init__(self, db: Session):
        self.db = db

    def trigger_payment_received(
        self,
        tenant_id: UUID,
        payment_id: str,
        invoice_id: Optional[str] = None,
        amount: float = 0,
        currency: str = "USD",
        payment_method: Optional[str] = None,
        reference_number: Optional[str] = None,
    ) -> bool:
        """
        Trigger webhook when payment is received

        Args:
            tenant_id: Tenant UUID
            payment_id: Payment unique identifier
            invoice_id: Associated invoice ID if available
            amount: Payment amount
            currency: Currency code (USD, EUR, etc.)
            payment_method: Payment method (credit_card, bank_transfer, etc.)
            reference_number: Payment provider reference

        Returns:
            True if webhook was enqueued, False otherwise
        """
        try:
            payload = WebhookFormatter.format_event_payload(
                event="payment.received",
                resource_type="payment",
                resource_id=payment_id,
                data={
                    "payment_id": payment_id,
                    "invoice_id": invoice_id,
                    "amount": str(amount),
                    "currency": currency,
                    "payment_method": payment_method,
                    "reference_number": reference_number,
                    "status": "completed",
                    "received_at": datetime.utcnow().isoformat(),
                },
                tenant_id=str(tenant_id),
            )
            result = self._enqueue_delivery(tenant_id, "payment.received", payload)
            if result:
                logger.info(f"Enqueued webhook for payment.received: {payment_id}")
            return result
        except Exception as e:
            logger.error(f"Error triggering payment.received webhook: {e}", exc_info=True)
            return False

    def trigger_payment_failed(
        self,
        tenant_id: UUID,
        payment_id: str,
        invoice_id: Optional[str] = None,
        amount: float = 0,
        currency: str = "USD",
        reason: Optional[str] = None,
        error_code: Optional[str] = None,
    ) -> bool:
        """
        Trigger webhook when payment fails

        Args:
            tenant_id: Tenant UUID
            payment_id: Payment unique identifier
            invoice_id: Associated invoice ID if available
            amount: Payment amount
            currency: Currency code
            reason: Failure reason
            error_code: Error code from payment provider

        Returns:
            True if webhook was enqueued, False otherwise
        """
        try:
            payload = WebhookFormatter.format_event_payload(
                event="payment.failed",
                resource_type="payment",
                resource_id=payment_id,
                data={
                    "payment_id": payment_id,
                    "invoice_id": invoice_id,
                    "amount": str(amount),
                    "currency": currency,
                    "reason": reason,
                    "error_code": error_code,
                    "status": "failed",
                    "failed_at": datetime.utcnow().isoformat(),
                },
                tenant_id=str(tenant_id),
            )
            result = self._enqueue_delivery(tenant_id, "payment.failed", payload)
            if result:
                logger.info(f"Enqueued webhook for payment.failed: {payment_id}")
            return result
        except Exception as e:
            logger.error(f"Error triggering payment.failed webhook: {e}", exc_info=True)
            return False

    def _enqueue_delivery(
        self, tenant_id: UUID, event: str, payload: Dict[str, Any]
    ) -> bool:
        """
        Internal method to enqueue webhook delivery for all active subscriptions

        Args:
            tenant_id: Tenant UUID
            event: Event name (e.g., "payment.received")
            payload: Event payload data

        Returns:
            True if at least one delivery was queued, False if no subscriptions found
        """
        try:
            tenant_id_str = str(tenant_id)

            # Check if there are active subscriptions for this event
            result = self.db.execute(
                text(
                    """
                    SELECT COUNT(*) FROM webhook_subscriptions
                    WHERE tenant_id = CAST(:tid AS uuid) AND event = :event AND active = true
                    """
                ),
                {"tid": tenant_id_str, "event": event},
            ).scalar()

            if not result:
                logger.debug(f"No active subscriptions for {event}")
                return False

            # Get all subscriptions for this event
            subs = self.db.execute(
                text(
                    """
                    SELECT url, secret FROM webhook_subscriptions
                    WHERE tenant_id = CAST(:tid AS uuid) AND event = :event AND active = true
                    """
                ),
                {"tid": tenant_id_str, "event": event},
            ).fetchall()

            # Create delivery records
            payload_json = json.dumps(payload, ensure_ascii=False)
            delivery_count = 0

            for url, secret in subs:
                self.db.execute(
                    text(
                        """
                        INSERT INTO webhook_deliveries(
                            tenant_id, event, payload, target_url, secret, status
                        )
                        VALUES (CAST(:tid AS uuid), :event, :payload::jsonb, :url, :secret, 'PENDING')
                        """
                    ),
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
