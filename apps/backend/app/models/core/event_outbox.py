"""Module: event_outbox.py

Event Outbox pattern – stores domain events for reliable async publishing."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import mapped_column

UUID = PGUUID(as_uuid=True)
from sqlalchemy import String as _String  # noqa: E402

TENANT_UUID = PGUUID(as_uuid=True).with_variant(_String(36), "sqlite")

from app.config.database import Base  # noqa: E402


class EventOutbox(Base):
    __tablename__ = "event_outbox"

    id = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(TENANT_UUID, ForeignKey("tenants.id"), index=True, nullable=False)
    event_type = mapped_column(String, nullable=False)
    aggregate_type = mapped_column(String, nullable=True)
    aggregate_id = mapped_column(UUID, nullable=True)
    payload = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    published_at = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count = mapped_column(Integer, default=0)
    last_error = mapped_column(Text, nullable=True)
    scheduled_at = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index(
            "ix_event_outbox_unpublished",
            "published_at",
            postgresql_where=text("published_at IS NULL"),
        ),
        Index("ix_event_outbox_tenant_event_type", "tenant_id", "event_type"),
        Index("ix_event_outbox_created_at", "created_at"),
    )
