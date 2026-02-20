"""Business logic for webhooks module."""

import logging
import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.webhooks.domain.events import WebhookEvent
from app.modules.webhooks.domain.exceptions import (
    InvalidWebhookURL,
    WebhookDisabled,
    WebhookNotFound,
)
from app.modules.webhooks.domain.models import EventType, WebhookDelivery, WebhookSubscription

logger = logging.getLogger(__name__)


class CreateWebhookSubscriptionUseCase:
    """Create a new webhook subscription."""

    def execute(
        self,
        *,
        tenant_id: UUID,
        event_type: EventType,
        target_url: str,
        secret: str,
        db_session: Session,
    ) -> WebhookSubscription:
        """Create webhook subscription."""
        if not target_url.startswith(("http://", "https://")):
            raise InvalidWebhookURL("URL must start with http:// or https://")

        subscription = WebhookSubscription(
            tenant_id=tenant_id,
            event_type=event_type,
            target_url=target_url,
            secret=secret,
            is_active=True,
        )

        db_session.add(subscription)
        db_session.commit()
        db_session.refresh(subscription)

        logger.info(f"Created webhook subscription: {subscription.id}")
        return subscription


class UpdateWebhookSubscriptionUseCase:
    """Update existing webhook subscription."""

    def execute(
        self,
        *,
        webhook_id: UUID,
        tenant_id: UUID,
        target_url: str | None = None,
        secret: str | None = None,
        is_active: bool | None = None,
        retry_count: int | None = None,
        timeout_seconds: int | None = None,
        db_session: Session = None,
    ) -> WebhookSubscription:
        """Update webhook subscription."""
        subscription = (
            db_session.query(WebhookSubscription)
            .filter(
                WebhookSubscription.id == webhook_id,
                WebhookSubscription.tenant_id == tenant_id,
            )
            .first()
        )

        if not subscription:
            raise WebhookNotFound(f"Webhook {webhook_id} not found")

        if target_url:
            if not target_url.startswith(("http://", "https://")):
                raise InvalidWebhookURL("URL must start with http:// or https://")
            subscription.target_url = target_url

        if secret:
            subscription.secret = secret
        if is_active is not None:
            subscription.is_active = is_active
        if retry_count is not None:
            subscription.retry_count = retry_count
        if timeout_seconds is not None:
            subscription.timeout_seconds = timeout_seconds

        subscription.updated_at = datetime.utcnow()
        db_session.commit()
        db_session.refresh(subscription)

        logger.info(f"Updated webhook subscription: {webhook_id}")
        return subscription


class DeleteWebhookSubscriptionUseCase:
    """Delete a webhook subscription."""

    def execute(
        self,
        *,
        webhook_id: UUID,
        tenant_id: UUID,
        db_session: Session,
    ) -> None:
        """Delete webhook subscription."""
        subscription = (
            db_session.query(WebhookSubscription)
            .filter(
                WebhookSubscription.id == webhook_id,
                WebhookSubscription.tenant_id == tenant_id,
            )
            .first()
        )

        if not subscription:
            raise WebhookNotFound(f"Webhook {webhook_id} not found")

        db_session.delete(subscription)
        db_session.commit()

        logger.info(f"Deleted webhook subscription: {webhook_id}")


class ListWebhooksUseCase:
    """List all webhook subscriptions for a tenant."""

    def execute(
        self,
        *,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100,
        db_session: Session = None,
    ) -> tuple[list[WebhookSubscription], int]:
        """List tenant's webhooks."""
        query = db_session.query(WebhookSubscription).filter(
            WebhookSubscription.tenant_id == tenant_id
        )

        total = query.count()
        webhooks = query.offset(skip).limit(limit).all()

        return webhooks, total


class TriggerWebhookEventUseCase:
    """Trigger a webhook event."""

    def execute(
        self,
        *,
        event: WebhookEvent,
        db_session: Session,
    ) -> int:
        """Trigger webhook event and queue deliveries."""
        subscriptions = (
            db_session.query(WebhookSubscription)
            .filter(
                WebhookSubscription.event_type == event.event_type,
                WebhookSubscription.tenant_id == event.tenant_id,
                WebhookSubscription.is_active,
            )
            .all()
        )

        logger.info(f"Found {len(subscriptions)} active webhooks for {event.event_type}")

        for subscription in subscriptions:
            delivery = WebhookDelivery(
                subscription_id=subscription.id,
                event_type=event.event_type,
                payload=event.to_dict(),
                attempt_number=1,
            )
            db_session.add(delivery)

        db_session.commit()

        return len(subscriptions)


class GetWebhookDeliveryHistoryUseCase:
    """Retrieve delivery history for a webhook."""

    def execute(
        self,
        *,
        webhook_id: UUID,
        tenant_id: UUID,
        limit: int = 100,
        skip: int = 0,
        db_session: Session = None,
    ) -> tuple[list[WebhookDelivery], int]:
        """Get delivery history."""
        subscription = (
            db_session.query(WebhookSubscription)
            .filter(
                WebhookSubscription.id == webhook_id,
                WebhookSubscription.tenant_id == tenant_id,
            )
            .first()
        )

        if not subscription:
            raise WebhookNotFound(f"Webhook {webhook_id} not found")

        query = (
            db_session.query(WebhookDelivery)
            .filter(WebhookDelivery.subscription_id == webhook_id)
            .order_by(WebhookDelivery.created_at.desc())
        )

        total = query.count()
        deliveries = query.offset(skip).limit(limit).all()

        return deliveries, total


class RetryFailedDeliveryUseCase:
    """Manually retry a failed delivery."""

    def execute(
        self,
        *,
        delivery_id: UUID,
        tenant_id: UUID,
        db_session: Session,
    ) -> WebhookDelivery:
        """Retry a failed delivery."""
        delivery = (
            db_session.query(WebhookDelivery)
            .join(WebhookSubscription)
            .filter(
                WebhookDelivery.id == delivery_id,
                WebhookSubscription.tenant_id == tenant_id,
            )
            .first()
        )

        if not delivery:
            raise WebhookNotFound(f"Delivery {delivery_id} not found")

        delivery.next_retry_at = datetime.utcnow()
        delivery.completed_at = None
        db_session.commit()
        db_session.refresh(delivery)

        logger.info(f"Queued delivery for retry: {delivery_id}")
        return delivery


class TestWebhookSubscriptionUseCase:
    """Test a webhook by sending sample event."""

    def execute(
        self,
        *,
        webhook_id: UUID,
        tenant_id: UUID,
        event_type: str | None = None,
        db_session: Session = None,
    ) -> WebhookDelivery:
        """Test webhook with sample event."""
        subscription = (
            db_session.query(WebhookSubscription)
            .filter(
                WebhookSubscription.id == webhook_id,
                WebhookSubscription.tenant_id == tenant_id,
            )
            .first()
        )

        if not subscription:
            raise WebhookNotFound(f"Webhook {webhook_id} not found")

        if not subscription.is_active:
            raise WebhookDisabled(f"Webhook {webhook_id} is disabled")

        test_event = WebhookEvent(
            event_type=event_type or subscription.event_type,
            event_id=f"test-{uuid.uuid4()}",
            timestamp=datetime.utcnow(),
            tenant_id=tenant_id,
            resource_type="Test",
            resource_id=uuid.uuid4(),
            data={"test": True, "message": "This is a test webhook"},
            metadata={"test": True},
        )

        delivery = WebhookDelivery(
            subscription_id=webhook_id,
            event_type=test_event.event_type,
            payload=test_event.to_dict(),
            attempt_number=1,
        )

        db_session.add(delivery)
        db_session.commit()
        db_session.refresh(delivery)

        logger.info(f"Created test delivery: {delivery.id}")
        return delivery
