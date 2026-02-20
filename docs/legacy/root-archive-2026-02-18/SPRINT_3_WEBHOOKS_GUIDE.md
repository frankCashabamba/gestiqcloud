# 📘 SPRINT 3: WEBHOOKS IMPLEMENTATION GUIDE
**Detailed technical guide for Tier 3 Webhooks module**

---

## 🎯 OVERVIEW

Webhooks allow external systems to subscribe to GestiqCloud events and receive HTTP callbacks when those events occur. Think of it as a pub/sub system for your ERP.

**Example:** When an invoice is created, automatically notify:
- Customer's accounting system
- Analytics dashboard
- Payment processor
- Email notification service

---

## 📦 FILE STRUCTURE

```
apps/webhooks/
├── __init__.py
├── domain/
│   ├── __init__.py
│   ├── models.py              # Database models
│   ├── events.py              # Event type definitions
│   └── exceptions.py          # Custom exceptions
├── application/
│   ├── __init__.py
│   ├── use_cases.py           # Business logic
│   ├── schemas.py             # Pydantic validation
│   └── services.py            # Webhook delivery service
├── interface/
│   ├── __init__.py
│   └── http/
│       ├── __init__.py
│       └── webhooks.py        # FastAPI router
└── infrastructure/
    ├── __init__.py
    ├── repository.py          # Database access
    ├── event_queue.py         # Redis/Celery queue
    ├── delivery.py            # HTTP delivery + retry
    └── providers.py           # Dependency injection
```

---

## 🗂️ STEP 1: DOMAIN MODELS (30 minutes)

### apps/webhooks/domain/models.py

```python
"""
Domain models for webhooks system.

Implements:
- WebhookSubscription: Configuration for webhook endpoints
- WebhookEvent: Event that triggered a webhook
- WebhookDelivery: Individual delivery attempt record
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from core.database import Base


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
    """
    Webhook subscription configuration.

    Stores URL and secret for external endpoints that want to
    receive notifications about specific events.

    Attributes:
        id: Unique identifier
        tenant_id: Which tenant owns this subscription
        event_type: EventType to subscribe to
        target_url: HTTP endpoint to deliver events to
        secret: HMAC secret for signing requests
        is_active: Whether to deliver events
        created_at: Subscription creation timestamp
        updated_at: Last update timestamp
        last_delivery_at: Timestamp of last successful delivery
    """
    __tablename__ = "webhook_subscriptions"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    target_url = Column(String(2048), nullable=False)
    secret = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    retry_count = Column(Integer, default=5)
    timeout_seconds = Column(Integer, default=30)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_delivery_at = Column(DateTime, nullable=True)

    # Relationships
    deliveries = relationship("WebhookDelivery", back_populates="subscription")

    def __repr__(self):
        return f"<WebhookSubscription {self.id}: {self.event_type}→{self.target_url}>"


class WebhookDelivery(Base):
    """
    Record of a single webhook delivery attempt.

    Tracks every attempt to deliver an event to a webhook URL,
    including success/failure and retry information.

    Attributes:
        id: Unique identifier
        subscription_id: Which subscription this delivery is for
        event_type: Type of event being delivered
        payload: JSON body sent to webhook
        status_code: HTTP response status code (null if not attempted)
        response_body: HTTP response body (for debugging)
        attempt_number: Which retry attempt this is
        next_retry_at: When to retry (null if not retrying)
        completed_at: When delivery completed (success or final failure)
        created_at: When this record was created
    """
    __tablename__ = "webhook_deliveries"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID, ForeignKey("webhook_subscriptions.id"))
    event_type = Column(String(50), nullable=False)
    payload = Column(JSON, nullable=False)

    # Delivery attempt info
    status_code = Column(Integer, nullable=True)
    response_body = Column(String(4096), nullable=True)
    error_message = Column(String(1024), nullable=True)

    # Retry tracking
    attempt_number = Column(Integer, default=1)
    next_retry_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

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

    def __repr__(self):
        status = "✓" if self.is_successful else "✗"
        return f"<WebhookDelivery {status} {self.event_type} attempt={self.attempt_number}>"
```

### apps/webhooks/domain/events.py

```python
"""
Event definitions for webhook system.

Defines what event data looks like when published.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID


@dataclass
class WebhookEvent:
    """
    Event payload structure for all webhooks.

    Attributes:
        event_type: Type of event (e.g., "invoice.created")
        event_id: Unique ID for this event
        timestamp: When event occurred
        tenant_id: Which tenant this is for
        resource_type: What kind of resource (e.g., "Invoice")
        resource_id: ID of the resource
        data: Event-specific data
        metadata: Additional context (user_id, ip_address, etc.)
    """
    event_type: str
    event_id: str
    timestamp: datetime
    tenant_id: UUID
    resource_type: str
    resource_id: UUID
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "event_type": self.event_type,
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "tenant_id": str(self.tenant_id),
            "resource_type": self.resource_type,
            "resource_id": str(self.resource_id),
            "data": self.data,
            "metadata": self.metadata or {},
        }


# Example events

@dataclass
class InvoiceCreatedEvent(WebhookEvent):
    """Invoice created event."""
    pass


@dataclass
class InvoicePaidEvent(WebhookEvent):
    """Invoice paid event."""
    pass


@dataclass
class ReceiptCreatedEvent(WebhookEvent):
    """Receipt created event."""
    pass
```

### apps/webhooks/domain/exceptions.py

```python
"""Custom exceptions for webhooks module."""


class WebhookException(Exception):
    """Base exception for webhook errors."""
    pass


class WebhookNotFound(WebhookException):
    """Webhook subscription not found."""
    pass


class InvalidWebhookURL(WebhookException):
    """Invalid webhook URL provided."""
    pass


class DeliveryFailed(WebhookException):
    """Webhook delivery failed."""
    pass


class WebhookDisabled(WebhookException):
    """Webhook is disabled."""
    pass
```

---

## 🔧 STEP 2: PYDANTIC SCHEMAS (20 minutes)

### apps/webhooks/application/schemas.py

```python
"""
Pydantic schemas for webhook endpoints.

Handles request/response validation.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, HttpUrl, Field
from uuid import UUID

from ..domain.events import EventType


class CreateWebhookRequest(BaseModel):
    """Request to create a webhook subscription."""
    event_type: EventType = Field(..., description="Event type to subscribe to")
    target_url: HttpUrl = Field(..., description="HTTP endpoint URL")
    secret: str = Field(..., min_length=8, description="HMAC secret (min 8 chars)")

    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "invoice.created",
                "target_url": "https://example.com/webhooks/invoice",
                "secret": "my-secret-key-12345"
            }
        }


class UpdateWebhookRequest(BaseModel):
    """Request to update a webhook subscription."""
    target_url: Optional[HttpUrl] = None
    secret: Optional[str] = Field(None, min_length=8)
    is_active: Optional[bool] = None
    retry_count: Optional[int] = Field(None, ge=1, le=10)

    class Config:
        json_schema_extra = {
            "example": {
                "is_active": True,
                "retry_count": 5
            }
        }


class WebhookResponse(BaseModel):
    """Response containing webhook subscription details."""
    id: UUID
    event_type: EventType
    target_url: str
    is_active: bool
    retry_count: int
    last_delivery_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WebhookListResponse(BaseModel):
    """Response containing list of webhook subscriptions."""
    items: List[WebhookResponse]
    total: int


class DeliveryResponse(BaseModel):
    """Response containing delivery attempt details."""
    id: UUID
    event_type: EventType
    status_code: Optional[int]
    attempt_number: int
    is_successful: bool
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DeliveryListResponse(BaseModel):
    """Response containing delivery history."""
    items: List[DeliveryResponse]
    total: int


class WebhookTestRequest(BaseModel):
    """Request to test a webhook with sample event."""
    event_type: Optional[str] = Field(None, description="Override event type")


class WebhookTestResponse(BaseModel):
    """Response from test webhook."""
    delivery_id: UUID
    status_code: Optional[int]
    response_body: Optional[str]
    success: bool
```

---

## 🎯 STEP 3: USE CASES (60 minutes)

### apps/webhooks/application/use_cases.py

```python
"""
Business logic for webhooks module.

Implements all webhook operations:
- Create/Update/Delete subscriptions
- Trigger events
- Manage delivery history
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID
import secrets
import json

from sqlalchemy.orm import Session

from ..domain.models import (
    WebhookSubscription,
    WebhookDelivery,
    EventType
)
from ..domain.events import WebhookEvent
from ..domain.exceptions import (
    WebhookNotFound,
    InvalidWebhookURL,
    WebhookDisabled
)

logger = logging.getLogger(__name__)


class CreateWebhookSubscriptionUseCase:
    """
    Create a new webhook subscription.

    Use case: User configures webhook at /webhooks endpoint
    """

    def execute(
        self,
        *,
        tenant_id: UUID,
        event_type: EventType,
        target_url: str,
        secret: str,
    ) -> Dict[str, Any]:
        """
        Create webhook subscription.

        Args:
            tenant_id: Which tenant owns this webhook
            event_type: Event type to subscribe to
            target_url: HTTP endpoint to deliver to
            secret: HMAC secret for signing

        Returns:
            Subscription details

        Raises:
            InvalidWebhookURL: If URL is malformed
        """
        # Validate URL
        if not target_url.startswith(('http://', 'https://')):
            raise InvalidWebhookURL("URL must start with http:// or https://")

        # TODO: Validate URL is reachable (optional, could test later)

        subscription = WebhookSubscription(
            tenant_id=tenant_id,
            event_type=event_type,
            target_url=target_url,
            secret=secret,
            is_active=True,
        )

        return {
            "id": subscription.id,
            "event_type": subscription.event_type,
            "target_url": subscription.target_url,
            "is_active": subscription.is_active,
            "created_at": subscription.created_at,
        }


class UpdateWebhookSubscriptionUseCase:
    """Update existing webhook subscription."""

    def execute(
        self,
        *,
        webhook_id: UUID,
        tenant_id: UUID,
        target_url: Optional[str] = None,
        secret: Optional[str] = None,
        is_active: Optional[bool] = None,
        retry_count: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Update webhook subscription.

        Args:
            webhook_id: Which webhook to update
            tenant_id: Verify ownership
            target_url: New URL (optional)
            secret: New secret (optional)
            is_active: Enable/disable (optional)
            retry_count: New retry count (optional)

        Returns:
            Updated subscription details
        """
        # TODO: Query DB, check ownership, update fields
        # Pattern is same as other update use cases

        return {
            "id": webhook_id,
            "message": "Webhook updated"
        }


class DeleteWebhookSubscriptionUseCase:
    """Delete a webhook subscription."""

    def execute(
        self,
        *,
        webhook_id: UUID,
        tenant_id: UUID,
    ) -> Dict[str, str]:
        """
        Delete webhook subscription.

        Args:
            webhook_id: Which webhook to delete
            tenant_id: Verify ownership

        Returns:
            Confirmation
        """
        # TODO: Query DB, check ownership, delete

        return {"message": "Webhook deleted"}


class ListWebhooksUseCase:
    """List all webhook subscriptions for a tenant."""

    def execute(
        self,
        *,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        List tenant's webhooks.

        Args:
            tenant_id: Which tenant
            skip: Pagination offset
            limit: Max results

        Returns:
            List of webhooks
        """
        # TODO: Query DB with filters and pagination

        return {
            "items": [],
            "total": 0,
            "skip": skip,
            "limit": limit,
        }


class TriggerWebhookEventUseCase:
    """
    Trigger a webhook event.

    Called when something happens (invoice created, etc).
    Finds all matching subscriptions and queues deliveries.
    """

    def execute(
        self,
        *,
        event: WebhookEvent,
        db_session: Session,
    ) -> Dict[str, Any]:
        """
        Trigger webhook event and queue deliveries.

        Args:
            event: Event that occurred
            db_session: Database session

        Returns:
            Count of subscriptions triggered
        """
        # Find all active subscriptions for this event
        subscriptions = db_session.query(WebhookSubscription).filter(
            WebhookSubscription.event_type == event.event_type,
            WebhookSubscription.tenant_id == event.tenant_id,
            WebhookSubscription.is_active == True,
        ).all()

        logger.info(f"Found {len(subscriptions)} active webhooks for {event.event_type}")

        # Queue delivery for each subscription
        for subscription in subscriptions:
            # TODO: Queue to Redis/Celery for async delivery
            delivery = WebhookDelivery(
                subscription_id=subscription.id,
                event_type=event.event_type,
                payload=event.to_dict(),
                attempt_number=1,
            )
            db_session.add(delivery)

        db_session.commit()

        return {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "subscriptions_triggered": len(subscriptions),
        }


class GetWebhookDeliveryHistoryUseCase:
    """Retrieve delivery history for a webhook."""

    def execute(
        self,
        *,
        webhook_id: UUID,
        tenant_id: UUID,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Get delivery history.

        Args:
            webhook_id: Which webhook
            tenant_id: Verify ownership
            limit: Max deliveries to return

        Returns:
            List of deliveries
        """
        # TODO: Query DB, return paginated deliveries

        return {
            "webhook_id": webhook_id,
            "items": [],
            "total": 0,
        }


class RetryFailedDeliveryUseCase:
    """Manually retry a failed delivery."""

    def execute(
        self,
        *,
        delivery_id: UUID,
        tenant_id: UUID,
    ) -> Dict[str, str]:
        """
        Retry a failed delivery.

        Args:
            delivery_id: Which delivery to retry
            tenant_id: Verify ownership

        Returns:
            Confirmation
        """
        # TODO: Find delivery, queue for retry

        return {"message": "Delivery queued for retry"}


class TestWebhookSubscriptionUseCase:
    """Test a webhook by sending sample event."""

    def execute(
        self,
        *,
        webhook_id: UUID,
        tenant_id: UUID,
        event_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Test webhook with sample event.

        Args:
            webhook_id: Which webhook to test
            tenant_id: Verify ownership
            event_type: Override event type

        Returns:
            Delivery result
        """
        # TODO: Find webhook, create sample event, deliver synchronously

        return {
            "delivery_id": "test-delivery-id",
            "status_code": None,
            "success": False,
        }
```

---

## 🌐 STEP 4: FASTAPI ENDPOINTS (40 minutes)

### apps/webhooks/interface/http/webhooks.py

```python
"""
FastAPI endpoints for webhooks module.

Endpoints:
- POST   /webhooks                 Create subscription
- GET    /webhooks                 List subscriptions
- PUT    /webhooks/{id}            Update subscription
- DELETE /webhooks/{id}            Delete subscription
- GET    /webhooks/{id}/history    Delivery history
- POST   /webhooks/{id}/test       Test webhook
"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from core.dependencies import get_current_user, get_db
from ..application.schemas import (
    CreateWebhookRequest,
    UpdateWebhookRequest,
    WebhookResponse,
    WebhookListResponse,
    DeliveryListResponse,
    WebhookTestRequest,
    WebhookTestResponse,
)
from ..application.use_cases import (
    CreateWebhookSubscriptionUseCase,
    UpdateWebhookSubscriptionUseCase,
    DeleteWebhookSubscriptionUseCase,
    ListWebhooksUseCase,
    TriggerWebhookEventUseCase,
    GetWebhookDeliveryHistoryUseCase,
    RetryFailedDeliveryUseCase,
    TestWebhookSubscriptionUseCase,
)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("", response_model=WebhookResponse)
async def create_webhook(
    request: CreateWebhookRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a webhook subscription.

    Example:
    ```bash
    curl -X POST http://localhost:8000/webhooks \
      -H "Authorization: Bearer <token>" \
      -H "Content-Type: application/json" \
      -d '{
        "event_type": "invoice.created",
        "target_url": "https://example.com/webhooks",
        "secret": "my-secret-key"
      }'
    ```
    """
    try:
        use_case = CreateWebhookSubscriptionUseCase()
        result = use_case.execute(
            tenant_id=current_user.tenant_id,
            event_type=request.event_type,
            target_url=str(request.target_url),
            secret=request.secret,
        )
        return WebhookResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=WebhookListResponse)
async def list_webhooks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all webhook subscriptions for current tenant.

    Query params:
    - skip: Pagination offset (default: 0)
    - limit: Max results (default: 100, max: 1000)
    """
    use_case = ListWebhooksUseCase()
    result = use_case.execute(
        tenant_id=current_user.tenant_id,
        skip=skip,
        limit=limit,
    )
    return WebhookListResponse(**result)


@router.put("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: UUID,
    request: UpdateWebhookRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update webhook subscription."""
    try:
        use_case = UpdateWebhookSubscriptionUseCase()
        result = use_case.execute(
            webhook_id=webhook_id,
            tenant_id=current_user.tenant_id,
            target_url=str(request.target_url) if request.target_url else None,
            secret=request.secret,
            is_active=request.is_active,
            retry_count=request.retry_count,
        )
        return WebhookResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: UUID,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete webhook subscription."""
    try:
        use_case = DeleteWebhookSubscriptionUseCase()
        result = use_case.execute(
            webhook_id=webhook_id,
            tenant_id=current_user.tenant_id,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{webhook_id}/history", response_model=DeliveryListResponse)
async def get_webhook_history(
    webhook_id: UUID,
    limit: int = Query(100, ge=1, le=1000),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get delivery history for a webhook."""
    use_case = GetWebhookDeliveryHistoryUseCase()
    result = use_case.execute(
        webhook_id=webhook_id,
        tenant_id=current_user.tenant_id,
        limit=limit,
    )
    return DeliveryListResponse(**result)


@router.post("/{webhook_id}/test", response_model=WebhookTestResponse)
async def test_webhook(
    webhook_id: UUID,
    request: WebhookTestRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Test webhook by sending sample event."""
    try:
        use_case = TestWebhookSubscriptionUseCase()
        result = use_case.execute(
            webhook_id=webhook_id,
            tenant_id=current_user.tenant_id,
            event_type=request.event_type,
        )
        return WebhookTestResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

---

## 🔄 STEP 5: INFRASTRUCTURE LAYER (90 minutes)

### apps/webhooks/infrastructure/delivery.py

```python
"""
Webhook delivery handler with retry logic.

Implements:
- HTTP delivery with HMAC-SHA256 signing
- Exponential backoff retry logic
- Delivery timeout handling
- Response logging
"""

import asyncio
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta
from typing import Optional
import httpx

from ..domain.models import WebhookDelivery, EventType

logger = logging.getLogger(__name__)


class WebhookDeliveryService:
    """Handle webhook HTTP delivery with retry logic."""

    # Retry configuration
    BASE_DELAY_SECONDS = 1  # Start with 1 second
    BACKOFF_MULTIPLIER = 2  # Double each time: 1s, 2s, 4s, 8s, 16s
    MAX_ATTEMPTS = 5

    def __init__(self, timeout_seconds: int = 30):
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _sign_payload(payload: dict, secret: str) -> str:
        """
        Create HMAC-SHA256 signature for webhook payload.

        This allows the receiving endpoint to verify the webhook
        came from GestiqCloud by computing the same signature.

        Args:
            payload: JSON payload to sign
            secret: Shared secret

        Returns:
            Hex-encoded HMAC signature
        """
        payload_json = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            secret.encode(),
            payload_json.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature

    async def deliver(
        self,
        delivery: WebhookDelivery,
        target_url: str,
        secret: str,
    ) -> bool:
        """
        Attempt to deliver a webhook.

        Args:
            delivery: WebhookDelivery record
            target_url: URL to deliver to
            secret: HMAC secret

        Returns:
            True if successful (200-299)
        """
        payload = delivery.payload
        signature = self._sign_payload(payload, secret)

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": f"sha256={signature}",
            "X-Webhook-ID": str(delivery.id),
            "X-Event-Type": delivery.event_type,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    target_url,
                    json=payload,
                    headers=headers,
                )

            delivery.status_code = response.status_code
            delivery.response_body = response.text[:4096]  # Truncate long responses

            if 200 <= response.status_code < 300:
                # Success!
                delivery.completed_at = datetime.utcnow()
                logger.info(
                    f"Webhook delivered successfully: {delivery.id} → {target_url}"
                )
                return True
            else:
                # Server returned error
                logger.warning(
                    f"Webhook delivery failed: {delivery.id} → {target_url} "
                    f"(status: {response.status_code})"
                )
                return False

        except asyncio.TimeoutError:
            delivery.error_message = "Timeout"
            logger.warning(f"Webhook timeout: {delivery.id} → {target_url}")
            return False

        except Exception as e:
            delivery.error_message = str(e)
            logger.exception(f"Webhook delivery error: {delivery.id} → {target_url}")
            return False

    def calculate_next_retry(self, attempt_number: int) -> Optional[datetime]:
        """
        Calculate when to retry based on exponential backoff.

        Retry schedule:
        - Attempt 1: Initial delivery (no retry)
        - Attempt 2: +1 second
        - Attempt 3: +2 seconds
        - Attempt 4: +4 seconds
        - Attempt 5: +8 seconds
        - Attempt 6: +16 seconds (then give up)

        Args:
            attempt_number: Current attempt (1-based)

        Returns:
            Datetime of next retry, or None if max attempts reached
        """
        if attempt_number >= self.MAX_ATTEMPTS:
            return None

        delay_seconds = self.BASE_DELAY_SECONDS * (
            self.BACKOFF_MULTIPLIER ** (attempt_number - 1)
        )
        return datetime.utcnow() + timedelta(seconds=delay_seconds)
```

### apps/webhooks/infrastructure/event_queue.py

```python
"""
Event queue implementation using Redis.

Queues webhook deliveries for async processing.
"""

import json
import logging
from typing import Dict, Any
from uuid import UUID
import redis

logger = logging.getLogger(__name__)


class WebhookEventQueue:
    """Redis-based queue for webhook deliveries."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self.redis_client = redis.from_url(redis_url)
        self.queue_key = "webhooks:deliveries"

    def enqueue(
        self,
        delivery_id: UUID,
        subscription_id: UUID,
        target_url: str,
        secret: str,
        payload: Dict[str, Any],
    ) -> bool:
        """
        Enqueue a webhook delivery.

        Args:
            delivery_id: Webhook delivery record ID
            subscription_id: Subscription ID
            target_url: Target URL
            secret: HMAC secret
            payload: Event payload

        Returns:
            True if enqueued successfully
        """
        try:
            message = {
                "delivery_id": str(delivery_id),
                "subscription_id": str(subscription_id),
                "target_url": target_url,
                "secret": secret,
                "payload": payload,
            }

            self.redis_client.rpush(
                self.queue_key,
                json.dumps(message)
            )

            logger.info(f"Enqueued webhook delivery: {delivery_id}")
            return True

        except Exception as e:
            logger.exception(f"Failed to enqueue webhook: {e}")
            return False

    def dequeue(self) -> Dict[str, Any]:
        """
        Dequeue next pending delivery.

        Returns:
            Message dict, or None if queue empty
        """
        try:
            message = self.redis_client.lpop(self.queue_key)
            if message:
                return json.loads(message)
            return None

        except Exception as e:
            logger.exception(f"Failed to dequeue webhook: {e}")
            return None

    def queue_size(self) -> int:
        """Get number of pending deliveries."""
        return self.redis_client.llen(self.queue_key)
```

---

## 📝 NEXT STEPS

Create these files:
1. ✓ `domain/models.py` - Database models
2. ✓ `domain/events.py` - Event definitions
3. ✓ `domain/exceptions.py` - Custom exceptions
4. ✓ `application/schemas.py` - Pydantic models
5. ✓ `application/use_cases.py` - Business logic
6. ✓ `interface/http/webhooks.py` - FastAPI endpoints
7. ✓ `infrastructure/delivery.py` - HTTP delivery
8. ✓ `infrastructure/event_queue.py` - Redis queue

Then complete:
9. `infrastructure/repository.py` - DB queries
10. `infrastructure/providers.py` - Dependency injection
11. `__init__.py` files - Module exports
12. Register router in `main.py`
13. Create database migrations
14. Add tests

---

## 🧪 TESTING CHECKLIST

```
□ Unit tests for use cases
□ Integration tests for endpoints
□ Delivery signing (HMAC-SHA256)
□ Retry logic (exponential backoff)
□ Event triggering
□ Database persistence
□ Error handling
□ Endpoint authorization
```

---

**Ready to start coding?** Begin with domain models, then work down the stack.
