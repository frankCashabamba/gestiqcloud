"""Business logic for notifications module."""

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.notifications.domain.exceptions import (
    DeliveryFailed,
    NotificationNotFound,
    TemplateNotFound,
)
from app.modules.notifications.domain.models import Notification, NotificationTemplate
from app.modules.notifications.infrastructure.notification_service import (
    NotificationChannel,
    NotificationPriority,
    NotificationService,
)

logger = logging.getLogger(__name__)


class SendNotificationUseCase:
    """Send a notification and persist it."""

    async def execute(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        channel: str,
        recipient: str,
        subject: str,
        body: str,
        priority: str = "medium",
        metadata: dict | None = None,
        db_session: Session,
    ) -> Notification:
        """Create notification record and send via provider."""
        notification = Notification(
            tenant_id=tenant_id,
            user_id=user_id,
            channel=channel,
            subject=subject,
            body=body,
            priority=priority,
            status="pending",
            metadata_=metadata,
        )
        db_session.add(notification)
        db_session.flush()

        try:
            service = NotificationService(db_session, {})
            result = await service.send(
                recipient=recipient,
                channel=NotificationChannel(channel),
                subject=subject,
                body=body,
                priority=NotificationPriority(priority),
                metadata=metadata,
            )
            notification.status = "sent" if result.get("success") else "failed"
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            notification.status = "failed"

        db_session.commit()
        db_session.refresh(notification)

        logger.info(f"Notification {notification.id} status: {notification.status}")
        return notification


class SendTemplateNotificationUseCase:
    """Send a notification using a template."""

    async def execute(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        template_name: str,
        channel: str,
        recipient: str,
        context: dict,
        priority: str = "medium",
        db_session: Session,
    ) -> Notification:
        """Load template, render, and send."""
        template = (
            db_session.query(NotificationTemplate)
            .filter(
                NotificationTemplate.tenant_id == tenant_id,
                NotificationTemplate.name == template_name,
                NotificationTemplate.is_active,
            )
            .first()
        )

        if not template:
            raise TemplateNotFound(f"Template '{template_name}' not found")

        try:
            subject = template.subject_template.format(**context)
            body = template.body_template.format(**context)
        except KeyError as e:
            raise DeliveryFailed(f"Missing template context key: {e}")

        use_case = SendNotificationUseCase()
        return await use_case.execute(
            tenant_id=tenant_id,
            user_id=user_id,
            channel=channel,
            recipient=recipient,
            subject=subject,
            body=body,
            priority=priority,
            db_session=db_session,
        )


class ListNotificationsUseCase:
    """List notifications for a tenant user."""

    def execute(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
        db_session: Session,
    ) -> tuple[list[Notification], int]:
        """List user's notifications."""
        query = (
            db_session.query(Notification)
            .filter(
                Notification.tenant_id == tenant_id,
                Notification.user_id == user_id,
            )
            .order_by(Notification.created_at.desc())
        )

        total = query.count()
        notifications = query.offset(skip).limit(limit).all()

        return notifications, total


class MarkAsReadUseCase:
    """Mark notification(s) as read."""

    def execute(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        notification_ids: list[UUID],
        db_session: Session,
    ) -> int:
        """Mark notifications as read. Returns count updated."""
        now = datetime.utcnow()
        count = (
            db_session.query(Notification)
            .filter(
                Notification.tenant_id == tenant_id,
                Notification.user_id == user_id,
                Notification.id.in_(notification_ids),
                Notification.read_at.is_(None),
            )
            .update(
                {"read_at": now, "status": "read", "updated_at": now},
                synchronize_session="fetch",
            )
        )

        db_session.commit()
        logger.info(f"Marked {count} notifications as read for user {user_id}")
        return count


class ArchiveNotificationUseCase:
    """Archive a notification."""

    def execute(
        self,
        *,
        notification_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        db_session: Session,
    ) -> Notification:
        """Archive a notification."""
        notification = (
            db_session.query(Notification)
            .filter(
                Notification.id == notification_id,
                Notification.tenant_id == tenant_id,
                Notification.user_id == user_id,
            )
            .first()
        )

        if not notification:
            raise NotificationNotFound(f"Notification {notification_id} not found")

        now = datetime.utcnow()
        notification.archived_at = now
        notification.status = "archived"
        notification.updated_at = now

        db_session.commit()
        db_session.refresh(notification)

        logger.info(f"Archived notification {notification_id}")
        return notification


class GetUnreadCountUseCase:
    """Get unread notification count for a user."""

    def execute(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        db_session: Session,
    ) -> int:
        """Count unread notifications."""
        return (
            db_session.query(Notification)
            .filter(
                Notification.tenant_id == tenant_id,
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
                Notification.archived_at.is_(None),
            )
            .count()
        )
