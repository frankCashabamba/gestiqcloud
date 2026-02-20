"""Domain models for notifications system."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.config.database import Base


class Notification(Base):
    """Notification record."""

    __tablename__ = "notifications"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, nullable=False, index=True)
    user_id = Column(UUID, nullable=False, index=True)
    channel = Column(String(20), nullable=False)  # email, sms, push, in_app
    subject = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)
    priority = Column(String(20), nullable=False, default="medium")  # low, medium, high, urgent
    status = Column(
        String(20), nullable=False, default="pending"
    )  # pending, sent, failed, read, archived
    metadata_ = Column("metadata", JSON, nullable=True)
    read_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Notification {self.id}: {self.channel} [{self.status}]>"


class NotificationTemplate(Base):
    """Notification template configuration."""

    __tablename__ = "notification_templates"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    channel = Column(String(20), nullable=False)
    subject_template = Column(String(500), nullable=False)
    body_template = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_notification_template_tenant_name"),
    )

    def __repr__(self):
        return f"<NotificationTemplate {self.id}: {self.name} ({self.channel})>"
