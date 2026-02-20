"""Pydantic schemas for notification endpoints."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class ChannelEnum(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"


class PriorityEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class SendNotificationRequest(BaseModel):
    """Request to send a notification."""

    channel: ChannelEnum
    recipient: str = Field(..., description="User ID or contact info")
    subject: str = Field(..., max_length=500)
    body: str
    priority: PriorityEnum = PriorityEnum.MEDIUM
    metadata: dict | None = None


class SendTemplateNotificationRequest(BaseModel):
    """Request to send a notification using a template."""

    template_name: str
    channel: ChannelEnum
    recipient: str = Field(..., description="User ID or contact info")
    context: dict = Field(default_factory=dict)
    priority: PriorityEnum = PriorityEnum.MEDIUM


class NotificationResponse(BaseModel):
    """Response containing notification details."""

    id: UUID
    channel: str
    subject: str
    body: str
    priority: str
    status: str
    read_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """Response containing list of notifications."""

    items: list[NotificationResponse]
    total: int
    skip: int
    limit: int


class MarkReadRequest(BaseModel):
    """Request to mark notifications as read."""

    notification_ids: list[UUID]


class UnreadCountResponse(BaseModel):
    """Response containing unread count."""

    count: int


class CreateTemplateRequest(BaseModel):
    """Request to create a notification template."""

    name: str = Field(..., max_length=100)
    channel: ChannelEnum
    subject_template: str = Field(..., max_length=500)
    body_template: str


class TemplateResponse(BaseModel):
    """Response containing template details."""

    id: UUID
    name: str
    channel: str
    subject_template: str
    body_template: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TemplateListResponse(BaseModel):
    """Response containing list of templates."""

    items: list[TemplateResponse]
    total: int
