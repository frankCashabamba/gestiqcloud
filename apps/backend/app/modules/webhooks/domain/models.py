"""Domain models for webhooks system."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.config.database import Base


class EventType(str, Enum):
    """Supported webhook event types."""

    # Sales events
    INVOICE_CREATED = "invoice.created"
    INVOICE_PAID = "invoice.paid"
    INVOICE_CANCELLED = "invoice.cancelled"

    # POS events
    RECEIPT_CREATED = "receipt.created"
    RECEIPT_PAID = "receipt.paid"

    # Inventory events
    STOCK_CREATED = "stock.created"
    STOCK_UPDATED = "stock.updated"
    STOCK_LOW_ALERT = "stock.low_alert"

    # Accounting events
    JOURNAL_ENTRY_CREATED = "journal_entry.created"
    RECONCILIATION_COMPLETED = "reconciliation.completed"

    # HR events
    PAYROLL_CREATED = "payroll.created"
    PAYROLL_COMPLETED = "payroll.completed"

    # System events
    BACKUP_COMPLETED = "backup.completed"
    ERROR_OCCURRED = "error.occurred"


class WebhookSubscription(Base):
    """Webhook subscription configuration."""

    __tablename__ = "webhook_subscriptions"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    target_url = Column(String(2048), nullable=False)
    secret = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    retry_count = Column(Integer, default=5)
    timeout_seconds = Column(Integer, default=30)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_delivery_at = Column(DateTime, nullable=True)

    # Relationships
    deliveries = relationship(
        "WebhookDelivery", back_populates="subscription", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<WebhookSubscription {self.id}: {self.event_type}→{self.target_url}>"


class WebhookDelivery(Base):
    """Record of a single webhook delivery attempt."""

    __tablename__ = "webhook_deliveries"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    subscription_id = Column(
        UUID, ForeignKey("webhook_subscriptions.id"), nullable=False, index=True
    )
    event_type = Column(String(50), nullable=False, index=True)
    payload = Column(JSON, nullable=False)

    # Delivery attempt info
    status_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    error_message = Column(String(1024), nullable=True)

    # Retry tracking
    attempt_number = Column(Integer, default=1)
    next_retry_at = Column(DateTime, nullable=True, index=True)
    completed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    subscription = relationship("WebhookSubscription", back_populates="deliveries")

    @property
    def is_successful(self) -> bool:
        """Check if delivery was successful."""
        return self.status_code is not None and 200 <= self.status_code < 300

    @property
    def is_pending(self) -> bool:
        """Check if delivery is pending retry."""
        return self.next_retry_at is not None and self.completed_at is None

    @property
    def is_failed(self) -> bool:
        """Check if delivery failed permanently."""
        return self.completed_at is not None and not self.is_successful

    def __repr__(self):
        status = "✓" if self.is_successful else "✗"
        return f"<WebhookDelivery {status} {self.event_type} attempt={self.attempt_number}>"
