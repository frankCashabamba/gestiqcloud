"""Webhook domain entities"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID


class WebhookEventType(str, Enum):
    """Supported webhook event types"""

    # Invoice events
    INVOICE_CREATED = "invoice.created"
    INVOICE_SENT = "invoice.sent"
    INVOICE_AUTHORIZED = "invoice.authorized"
    INVOICE_REJECTED = "invoice.rejected"
    INVOICE_CANCELLED = "invoice.cancelled"

    # Sales events
    SALES_ORDER_CREATED = "sales_order.created"
    SALES_ORDER_CONFIRMED = "sales_order.confirmed"
    SALES_ORDER_CANCELLED = "sales_order.cancelled"

    # Payment events
    PAYMENT_RECEIVED = "payment.received"
    PAYMENT_FAILED = "payment.failed"

    # Inventory events
    INVENTORY_LOW = "inventory.low"
    INVENTORY_UPDATED = "inventory.updated"

    # Purchase events
    PURCHASE_ORDER_CREATED = "purchase_order.created"
    PURCHASE_RECEIVED = "purchase_received"

    # Customer events
    CUSTOMER_CREATED = "customer.created"
    CUSTOMER_UPDATED = "customer.updated"

    # Generic events
    DOCUMENT_UPDATED = "document.updated"
    ERROR_OCCURRED = "error.occurred"


class WebhookStatus(str, Enum):
    """Webhook status"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class DeliveryStatus(str, Enum):
    """Delivery status for webhook attempts"""

    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    ABANDONED = "abandoned"


@dataclass
class WebhookEndpoint:
    """Webhook endpoint configuration"""

    id: UUID
    tenant_id: str
    url: str
    events: list[WebhookEventType]
    secret: str  # For HMAC signature
    status: WebhookStatus = WebhookStatus.ACTIVE
    active: bool = True
    headers: dict[str, str] | None = None
    max_retries: int = 5
    timeout_seconds: int = 30
    batch_size: int = 1  # Events per request
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class WebhookEvent:
    """Webhook event to be delivered"""

    id: UUID
    webhook_id: UUID
    tenant_id: str
    event_type: WebhookEventType
    resource_type: str  # 'invoice', 'sales_order', etc.
    resource_id: str
    payload: dict[str, Any]
    timestamp: datetime
    delivered: bool = False
    delivery_status: DeliveryStatus = DeliveryStatus.PENDING
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class WebhookDeliveryAttempt:
    """Record of webhook delivery attempt"""

    id: UUID
    webhook_id: UUID
    event_id: UUID
    attempt_number: int
    status: DeliveryStatus
    http_status_code: int | None = None
    response_body: str | None = None
    error_message: str | None = None
    request_timestamp: datetime = None
    response_timestamp: datetime | None = None
    next_retry_at: datetime | None = None
    created_at: datetime = None

    def __post_init__(self):
        if self.request_timestamp is None:
            self.request_timestamp = datetime.now()
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class WebhookTrigger:
    """Definition of when webhooks are triggered"""

    event_type: WebhookEventType
    resource_type: str
    conditions: dict[str, Any] | None = None  # Additional conditions
    immediate: bool = True  # Trigger immediately or batch
    batch_window_seconds: int = 60  # For batched events


@dataclass
class WebhookPayload:
    """Standard webhook payload structure"""

    id: str
    timestamp: datetime
    event: WebhookEventType
    data: dict[str, Any]
    tenant_id: str
    resource_type: str
    resource_id: str

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "event": self.event.value,
            "data": self.data,
            "tenant_id": self.tenant_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
        }
