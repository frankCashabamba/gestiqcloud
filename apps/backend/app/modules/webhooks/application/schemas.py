"""Pydantic schemas for webhook endpoints."""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, HttpUrl, Field
from uuid import UUID

from app.modules.webhooks.domain.models import EventType


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
    timeout_seconds: Optional[int] = Field(None, ge=5, le=300)
    
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
    timeout_seconds: int
    last_delivery_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class WebhookListResponse(BaseModel):
    """Response containing list of webhook subscriptions."""
    items: List[WebhookResponse]
    total: int
    skip: int
    limit: int


class DeliveryResponse(BaseModel):
    """Response containing delivery attempt details."""
    id: UUID
    event_type: str
    status_code: Optional[int] = None
    attempt_number: int
    is_successful: bool
    is_pending: bool
    is_failed: bool
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class DeliveryListResponse(BaseModel):
    """Response containing delivery history."""
    items: List[DeliveryResponse]
    total: int
    webhook_id: UUID


class WebhookTestRequest(BaseModel):
    """Request to test a webhook with sample event."""
    event_type: Optional[str] = Field(None, description="Override event type")


class WebhookTestResponse(BaseModel):
    """Response from test webhook."""
    delivery_id: UUID
    status_code: Optional[int] = None
    response_body: Optional[str] = None
    success: bool
    message: str
