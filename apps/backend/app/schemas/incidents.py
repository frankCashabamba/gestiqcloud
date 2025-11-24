from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, validator


class IncidentCreate(BaseModel):
    type: Literal["error", "warning", "bug", "feature_request", "stock_alert"] = Field(
        ..., description="Incident type"
    )
    severity: Literal["low", "medium", "high", "critical"] = Field(
        ..., description="Severity level"
    )
    title: str = Field(..., min_length=1, max_length=255, description="Short title")
    description: str | None = Field(None, description="Detailed description")
    stack_trace: str | None = Field(None, description="Stack trace if technical error")
    context: dict[str, Any] | None = Field(None, description="Additional context (JSON)")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "error",
                "severity": "high",
                "title": "Error processing product import",
                "description": "Failed validating CSV at line 45",
                "stack_trace": "Traceback...",
                "context": {"file_id": "abc-123", "line": 45},
            }
        }


class IncidentUpdate(BaseModel):
    status: Literal["open", "in_progress", "resolved", "closed"] | None = None
    assigned_to: UUID | None = None
    ia_analysis: dict[str, Any] | None = None
    ia_suggestion: str | None = None


class IncidentResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    type: str
    severity: str
    title: str
    description: str | None
    stack_trace: str | None
    context: dict[str, Any] | None
    status: str
    assigned_to: UUID | None
    auto_detected: bool
    auto_resolved: bool
    ia_analysis: dict[str, Any] | None
    ia_suggestion: str | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


class IncidentAnalysisRequest(BaseModel):
    use_gpt4: bool = Field(False, description="Usar GPT-4 en lugar de GPT-3.5")
    include_code_suggestions: bool = Field(True, description="Incluir sugerencias de código")


class IncidentAnalysisResponse(BaseModel):
    incident_id: UUID
    analysis: dict[str, Any]
    suggestion: str | None
    confidence_score: float | None
    processing_time_ms: int


class StockAlertCreate(BaseModel):
    product_id: UUID
    warehouse_id: UUID | None = None
    alert_type: Literal["low_stock", "out_of_stock", "expiring", "expired", "overstock"]
    current_qty: int
    threshold_qty: int | None = None
    threshold_config: dict[str, Any] | None = None


class StockAlertResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    product_id: UUID
    warehouse_id: UUID | None
    alert_type: str
    threshold_config: dict[str, Any] | None
    current_qty: int | None
    threshold_qty: int | None
    status: str
    incident_id: UUID | None
    ia_recommendation: str | None
    notified_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationChannelCreate(BaseModel):
    channel_type: Literal["email", "whatsapp", "telegram", "slack"]
    name: str = Field(..., min_length=1, max_length=100)
    config: dict[str, Any] = Field(
        ..., description="Channel configuration (API keys, webhooks, etc)"
    )
    is_active: bool = True
    priority: int = Field(0, ge=0, le=100)

    @validator("config")
    def validate_config(cls, v, values):
        channel_type = values.get("channel_type")
        if channel_type == "email":
            if "smtp_host" not in v or "from_email" not in v:
                raise ValueError("Email config requires smtp_host and from_email")
        elif channel_type == "whatsapp":
            if "api_key" not in v or "phone" not in v:
                raise ValueError("WhatsApp config requires api_key and phone")
        elif channel_type == "telegram":
            if "bot_token" not in v or "chat_id" not in v:
                raise ValueError("Telegram config requires bot_token and chat_id")
        elif channel_type == "slack":
            if "webhook_url" not in v:
                raise ValueError("Slack config requires webhook_url")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "channel_type": "telegram",
                "name": "Primary Stock Alerts",
                "config": {
                    "bot_token": "123456:ABC-DEF...",
                    "chat_id": "-1001234567890",
                },
                "is_active": True,
                "priority": 10,
            }
        }


class NotificationChannelUpdate(BaseModel):
    name: str | None = None
    config: dict[str, Any] | None = None
    is_active: bool | None = None
    priority: int | None = Field(None, ge=0, le=100)


class NotificationChannelResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    channel_type: str
    name: str
    config: dict[str, Any]
    is_active: bool
    priority: int
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


class NotificationLogResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    channel_id: UUID | None
    incident_id: UUID | None
    stock_alert_id: UUID | None
    notification_type: str
    recipient: str
    subject: str | None
    status: str
    error_message: str | None
    sent_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class SendNotificationRequest(BaseModel):
    channel_id: UUID
    recipient: str
    subject: str | None = None
    body: str
    metadata: dict[str, Any] | None = None
