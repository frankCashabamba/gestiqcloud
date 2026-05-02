"""Pydantic schemas for webhook endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from app.modules.webhooks.domain.models import EventType


class CreateWebhookRequest(BaseModel):
    """Request to create a webhook subscription."""

    event_type: EventType = Field(..., description="Event type to subscribe to")
    target_url: HttpUrl = Field(..., description="HTTP endpoint URL")
    secret: str = Field(..., min_length=8, description="HMAC secret (min 8 chars)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event_type": "invoice.created",
                "target_url": "https://example.com/webhooks/invoice",
                "secret": "my-secret-key-12345",
            }
        }
    )


class UpdateWebhookRequest(BaseModel):
    """Request to update a webhook subscription."""

    target_url: HttpUrl | None = None
    secret: str | None = Field(None, min_length=8)
    is_active: bool | None = None
    retry_count: int | None = Field(None, ge=1, le=10)
    timeout_seconds: int | None = Field(None, ge=5, le=300)

    model_config = ConfigDict(json_schema_extra={"example": {"is_active": True, "retry_count": 5}})


class WebhookResponse(BaseModel):
    """Response containing webhook subscription details."""

    id: UUID
    event_type: EventType
    target_url: str
    is_active: bool
    retry_count: int
    timeout_seconds: int
    last_delivery_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    # Masked representation of the signing secret. Only the last 4 chars are
    # exposed so the UI can show e.g. "***abcd" without leaking the full key.
    secret_masked: str | None = None
    # The full secret is intentionally excluded from the serialized response.
    # It is loaded from the ORM object only to compute `secret_masked`.
    secret: str | None = Field(default=None, exclude=True, repr=False)

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def _mask_secret(self) -> "WebhookResponse":
        if self.secret:
            self.secret_masked = "***" + self.secret[-4:]
        # Wipe full secret so it never leaks even if downstream code dumps the
        # model with `exclude` overrides.
        self.secret = None
        return self


class WebhookListResponse(BaseModel):
    """Response containing list of webhook subscriptions."""

    items: list[WebhookResponse]
    total: int
    skip: int
    limit: int


class DeliveryResponse(BaseModel):
    """Response containing delivery attempt details."""

    id: UUID
    event_type: str
    status_code: int | None = None
    attempt_number: int
    is_successful: bool
    is_pending: bool
    is_failed: bool
    created_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class DeliveryListResponse(BaseModel):
    """Response containing delivery history."""

    items: list[DeliveryResponse]
    total: int
    webhook_id: UUID


class WebhookTestRequest(BaseModel):
    """Request to test a webhook with sample event."""

    event_type: str | None = Field(None, description="Override event type")


class WebhookTestResponse(BaseModel):
    """Response from test webhook."""

    delivery_id: UUID
    status_code: int | None = None
    response_body: str | None = None
    success: bool
    message: str


class WebhookSecretResponse(BaseModel):
    """Response containing the real signing secret (privileged endpoint)."""

    webhook_id: UUID
    signing_secret: str
