"""Event Outbox Service — Publish domain events with guaranteed delivery"""
import logging
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.models.core.event_outbox import EventOutbox

logger = logging.getLogger(__name__)


class EventService:
    """Service for publishing domain events to the outbox."""

    @staticmethod
    def publish(
        db: Session,
        tenant_id: UUID,
        event_type: str,
        payload: dict[str, Any],
        aggregate_type: str | None = None,
        aggregate_id: UUID | None = None,
    ) -> EventOutbox:
        """Publish an event to the outbox (within current transaction)."""
        event = EventOutbox(
            id=uuid4(),
            tenant_id=tenant_id,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
        )
        db.add(event)
        # Don't commit — let caller's transaction include this
        return event

    @staticmethod
    def mark_published(db: Session, event_id: UUID) -> None:
        """Mark an event as published."""
        event = db.query(EventOutbox).filter(EventOutbox.id == event_id).first()
        if event:
            event.published_at = datetime.utcnow()
            event.last_error = None

    @staticmethod
    def mark_failed(db: Session, event_id: UUID, error: str) -> None:
        """Mark an event as failed with error."""
        event = db.query(EventOutbox).filter(EventOutbox.id == event_id).first()
        if event:
            event.retry_count = (event.retry_count or 0) + 1
            event.last_error = error

    @staticmethod
    def get_unpublished(db: Session, limit: int = 50, max_retries: int = 5) -> list[EventOutbox]:
        """Get unpublished events for processing."""
        return (
            db.query(EventOutbox)
            .filter(
                EventOutbox.published_at.is_(None),
                EventOutbox.retry_count < max_retries,
            )
            .order_by(EventOutbox.created_at.asc())
            .limit(limit)
            .all()
        )
