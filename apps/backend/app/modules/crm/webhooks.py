"""
Webhook triggers for CRM module

Handles sending webhook events when customers/leads are created or updated.
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


class CustomerWebhookService:
    """Service for triggering webhooks from CRM module"""

    def __init__(self, db: Session):
        self.db = db

    def trigger_customer_created(
        self,
        tenant_id: UUID,
        customer_id: str,
        customer_name: str,
        customer_email: str | None = None,
        customer_phone: str | None = None,
        customer_type: str = "individual",
    ) -> bool:
        """
        Trigger webhook when customer/lead is created

        Args:
            tenant_id: Tenant UUID
            customer_id: Customer/Lead unique identifier
            customer_name: Customer business or personal name
            customer_email: Customer email address
            customer_phone: Customer phone number
            customer_type: Type of customer (individual, company, etc.)

        Returns:
            True if webhook was enqueued, False otherwise
        """
        try:
            payload = WebhookFormatter.format_event_payload(
                event="customer.created",
                resource_type="customer",
                resource_id=customer_id,
                data={
                    "customer_id": customer_id,
                    "customer_name": customer_name,
                    "customer_email": customer_email,
                    "customer_phone": customer_phone,
                    "customer_type": customer_type,
                    "status": "active",
                    "created_at": datetime.utcnow().isoformat(),
                },
                tenant_id=str(tenant_id),
            )
            result = self._enqueue_delivery(tenant_id, "customer.created", payload)
            if result:
                logger.info(f"Enqueued webhook for customer.created: {customer_id}")
            return result
        except Exception as e:
            logger.error(f"Error triggering customer.created webhook: {e}", exc_info=True)
            return False

    def trigger_customer_updated(
        self,
        tenant_id: UUID,
        customer_id: str,
        customer_name: str,
        customer_email: str | None = None,
        customer_phone: str | None = None,
        changes: dict[str, Any] | None = None,
    ) -> bool:
        """
        Trigger webhook when customer/lead is updated

        Args:
            tenant_id: Tenant UUID
            customer_id: Customer/Lead unique identifier
            customer_name: Updated customer name
            customer_email: Updated customer email
            customer_phone: Updated customer phone
            changes: Dictionary of field changes (field_name -> new_value)

        Returns:
            True if webhook was enqueued, False otherwise
        """
        try:
            payload = WebhookFormatter.format_event_payload(
                event="customer.updated",
                resource_type="customer",
                resource_id=customer_id,
                data={
                    "customer_id": customer_id,
                    "customer_name": customer_name,
                    "customer_email": customer_email,
                    "customer_phone": customer_phone,
                    "changes": changes or {},
                    "status": "active",
                    "updated_at": datetime.utcnow().isoformat(),
                },
                tenant_id=str(tenant_id),
            )
            result = self._enqueue_delivery(tenant_id, "customer.updated", payload)
            if result:
                logger.info(f"Enqueued webhook for customer.updated: {customer_id}")
            return result
        except Exception as e:
            logger.error(f"Error triggering customer.updated webhook: {e}", exc_info=True)
            return False

    def _enqueue_delivery(self, tenant_id: UUID, event: str, payload: dict[str, Any]) -> bool:
        """
        Internal method to enqueue webhook delivery for all active subscriptions

        Args:
            tenant_id: Tenant UUID
            event: Event name (e.g., "customer.created")
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
