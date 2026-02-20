"""
Webhook triggers for invoicing module

Handles sending webhook events when invoices are created, sent, authorized, rejected, etc.
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


class InvoicingWebhookService:
    """Service for triggering webhooks from invoicing module"""

    def __init__(self, db: Session):
        self.db = db

    def trigger_invoice_created(
        self,
        tenant_id: UUID,
        invoice_id: str,
        invoice_number: str,
        amount: float,
        currency: str,
        customer_name: str,
        customer_id: str | None = None,
        status: str = "draft",
    ) -> bool:
        """
        Trigger webhook when invoice is created

        Args:
            tenant_id: Tenant UUID
            invoice_id: Invoice unique identifier
            invoice_number: Human-readable invoice number
            amount: Total amount
            currency: Currency code (USD, EUR, etc.)
            customer_name: Customer business name
            customer_id: Customer ID if available
            status: Invoice status (default: draft)

        Returns:
            True if webhook was enqueued, False otherwise
        """
        try:
            payload = WebhookFormatter.format_event_payload(
                event="invoice.created",
                resource_type="invoice",
                resource_id=invoice_id,
                data={
                    "invoice_id": invoice_id,
                    "invoice_number": invoice_number,
                    "amount": str(amount),
                    "currency": currency,
                    "customer_name": customer_name,
                    "customer_id": customer_id,
                    "status": status,
                    "created_at": datetime.utcnow().isoformat(),
                },
                tenant_id=str(tenant_id),
            )
            result = self._enqueue_delivery(tenant_id, "invoice.created", payload)
            if result:
                logger.info(f"Enqueued webhook for invoice.created: {invoice_id}")
            return result
        except Exception as e:
            logger.error(f"Error triggering invoice.created webhook: {e}", exc_info=True)
            return False

    def trigger_invoice_sent(
        self,
        tenant_id: UUID,
        invoice_id: str,
        invoice_number: str,
        sent_to: str | None = None,
    ) -> bool:
        """
        Trigger webhook when invoice is sent (email, etc.)

        Args:
            tenant_id: Tenant UUID
            invoice_id: Invoice unique identifier
            invoice_number: Human-readable invoice number
            sent_to: Email or recipient identifier

        Returns:
            True if webhook was enqueued, False otherwise
        """
        try:
            payload = WebhookFormatter.format_event_payload(
                event="invoice.sent",
                resource_type="invoice",
                resource_id=invoice_id,
                data={
                    "invoice_id": invoice_id,
                    "invoice_number": invoice_number,
                    "sent_to": sent_to,
                    "status": "sent",
                    "sent_at": datetime.utcnow().isoformat(),
                },
                tenant_id=str(tenant_id),
            )
            result = self._enqueue_delivery(tenant_id, "invoice.sent", payload)
            if result:
                logger.info(f"Enqueued webhook for invoice.sent: {invoice_id}")
            return result
        except Exception as e:
            logger.error(f"Error triggering invoice.sent webhook: {e}", exc_info=True)
            return False

    def trigger_invoice_authorized(
        self,
        tenant_id: UUID,
        invoice_id: str,
        invoice_number: str,
        authorization_number: str,
        authorization_key: str | None = None,
    ) -> bool:
        """
        Trigger webhook when invoice is authorized in SRI

        Args:
            tenant_id: Tenant UUID
            invoice_id: Invoice unique identifier
            invoice_number: Human-readable invoice number
            authorization_number: SRI authorization number
            authorization_key: SRI authorization key

        Returns:
            True if webhook was enqueued, False otherwise
        """
        try:
            payload = WebhookFormatter.format_event_payload(
                event="invoice.authorized",
                resource_type="invoice",
                resource_id=invoice_id,
                data={
                    "invoice_id": invoice_id,
                    "invoice_number": invoice_number,
                    "authorization_number": authorization_number,
                    "authorization_key": authorization_key,
                    "status": "authorized",
                    "authorized_at": datetime.utcnow().isoformat(),
                },
                tenant_id=str(tenant_id),
            )
            result = self._enqueue_delivery(tenant_id, "invoice.authorized", payload)
            if result:
                logger.info(f"Enqueued webhook for invoice.authorized: {invoice_id}")
            return result
        except Exception as e:
            logger.error(f"Error triggering invoice.authorized webhook: {e}", exc_info=True)
            return False

    def trigger_invoice_rejected(
        self,
        tenant_id: UUID,
        invoice_id: str,
        invoice_number: str,
        reason: str,
        error_code: str | None = None,
    ) -> bool:
        """
        Trigger webhook when invoice is rejected (SRI rejection, validation, etc.)

        Args:
            tenant_id: Tenant UUID
            invoice_id: Invoice unique identifier
            invoice_number: Human-readable invoice number
            reason: Rejection reason
            error_code: SRI error code if available

        Returns:
            True if webhook was enqueued, False otherwise
        """
        try:
            payload = WebhookFormatter.format_event_payload(
                event="invoice.rejected",
                resource_type="invoice",
                resource_id=invoice_id,
                data={
                    "invoice_id": invoice_id,
                    "invoice_number": invoice_number,
                    "reason": reason,
                    "error_code": error_code,
                    "status": "rejected",
                    "rejected_at": datetime.utcnow().isoformat(),
                },
                tenant_id=str(tenant_id),
            )
            result = self._enqueue_delivery(tenant_id, "invoice.rejected", payload)
            if result:
                logger.info(f"Enqueued webhook for invoice.rejected: {invoice_id}")
            return result
        except Exception as e:
            logger.error(f"Error triggering invoice.rejected webhook: {e}", exc_info=True)
            return False

    def trigger_invoice_cancelled(
        self,
        tenant_id: UUID,
        invoice_id: str,
        invoice_number: str,
        reason: str | None = None,
    ) -> bool:
        """
        Trigger webhook when invoice is cancelled

        Args:
            tenant_id: Tenant UUID
            invoice_id: Invoice unique identifier
            invoice_number: Human-readable invoice number
            reason: Cancellation reason

        Returns:
            True if webhook was enqueued, False otherwise
        """
        try:
            payload = WebhookFormatter.format_event_payload(
                event="invoice.cancelled",
                resource_type="invoice",
                resource_id=invoice_id,
                data={
                    "invoice_id": invoice_id,
                    "invoice_number": invoice_number,
                    "reason": reason,
                    "status": "cancelled",
                    "cancelled_at": datetime.utcnow().isoformat(),
                },
                tenant_id=str(tenant_id),
            )
            result = self._enqueue_delivery(tenant_id, "invoice.cancelled", payload)
            if result:
                logger.info(f"Enqueued webhook for invoice.cancelled: {invoice_id}")
            return result
        except Exception as e:
            logger.error(f"Error triggering invoice.cancelled webhook: {e}", exc_info=True)
            return False

    def _enqueue_delivery(self, tenant_id: UUID, event: str, payload: dict[str, Any]) -> bool:
        """
        Internal method to enqueue webhook delivery for all active subscriptions

        Args:
            tenant_id: Tenant UUID
            event: Event name (e.g., "invoice.created")
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
