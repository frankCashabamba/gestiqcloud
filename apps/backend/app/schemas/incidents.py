from datetime import datetime
from typing import Optional, Literal, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, validator


class IncidentCreate(BaseModel):
    tipo: Literal["error", "warning", "bug", "feature_request", "stock_alert"] = Field(
        ..., description="Tipo de incidencia"
    )
    severidad: Literal["low", "medium", "high", "critical"] = Field(
        ..., description="Nivel de severidad"
    )
    titulo: str = Field(
        ..., min_length=1, max_length=255, description="Título descriptivo"
    )
    description: Optional[str] = Field(None, description="Descripción detallada")
    stack_trace: Optional[str] = Field(
        None, description="Stack trace si es error técnico"
    )
    context: Optional[Dict[str, Any]] = Field(
        None, description="Contexto adicional (JSON)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "tipo": "error",
                "severidad": "high",
                "titulo": "Error al procesar importación de productos",
                "descripcion": "Fallo al validar archivo CSV línea 45",
                "stack_trace": "Traceback...",
                "context": {"file_id": "abc-123", "line": 45},
            }
        }


class IncidentUpdate(BaseModel):
    estado: Optional[Literal["open", "in_progress", "resolved", "closed"]] = None
    assigned_to: Optional[UUID] = None
    ia_analysis: Optional[Dict[str, Any]] = None
    ia_suggestion: Optional[str] = None


class IncidentResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    tipo: str
    severidad: str
    titulo: str
    description: Optional[str]
    stack_trace: Optional[str]
    context: Optional[Dict[str, Any]]
    estado: str
    assigned_to: Optional[UUID]
    auto_detected: bool
    auto_resolved: bool
    ia_analysis: Optional[Dict[str, Any]]
    ia_suggestion: Optional[str]
    resolved_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class IncidentAnalysisRequest(BaseModel):
    use_gpt4: bool = Field(False, description="Usar GPT-4 en lugar de GPT-3.5")
    include_code_suggestions: bool = Field(
        True, description="Incluir sugerencias de código"
    )


class IncidentAnalysisResponse(BaseModel):
    incident_id: UUID
    analysis: Dict[str, Any]
    suggestion: Optional[str]
    confidence_score: Optional[float]
    processing_time_ms: int


class StockAlertCreate(BaseModel):
    product_id: UUID
    warehouse_id: Optional[UUID] = None
    alert_type: Literal["low_stock", "out_of_stock", "expiring", "expired", "overstock"]
    current_qty: int
    threshold_qty: Optional[int] = None
    threshold_config: Optional[Dict[str, Any]] = None


class StockAlertResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    product_id: UUID
    warehouse_id: Optional[UUID]
    alert_type: str
    threshold_config: Optional[Dict[str, Any]]
    current_qty: Optional[int]
    threshold_qty: Optional[int]
    status: str
    incident_id: Optional[UUID]
    ia_recommendation: Optional[str]
    notified_at: Optional[datetime]
    resolved_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationChannelCreate(BaseModel):
    tipo: Literal["email", "whatsapp", "telegram", "slack"]
    name: str = Field(..., min_length=1, max_length=100)
    config: Dict[str, Any] = Field(
        ..., description="Configuración del canal (API keys, webhooks, etc)"
    )
    is_active: bool = True
    priority: int = Field(0, ge=0, le=100)

    @validator("config")
    def validate_config(cls, v, values):
        tipo = values.get("tipo")
        if tipo == "email":
            if "smtp_host" not in v or "from_email" not in v:
                raise ValueError("Email config requires smtp_host and from_email")
        elif tipo == "whatsapp":
            if "api_key" not in v or "phone" not in v:
                raise ValueError("WhatsApp config requires api_key and phone")
        elif tipo == "telegram":
            if "bot_token" not in v or "chat_id" not in v:
                raise ValueError("Telegram config requires bot_token and chat_id")
        elif tipo == "slack":
            if "webhook_url" not in v:
                raise ValueError("Slack config requires webhook_url")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "tipo": "telegram",
                "name": "Alertas Stock Principal",
                "config": {
                    "bot_token": "123456:ABC-DEF...",
                    "chat_id": "-1001234567890",
                },
                "is_active": True,
                "priority": 10,
            }
        }


class NotificationChannelUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0, le=100)


class NotificationChannelResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    tipo: str
    name: str
    config: Dict[str, Any]
    is_active: bool
    priority: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class NotificationLogResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    channel_id: Optional[UUID]
    incident_id: Optional[UUID]
    stock_alert_id: Optional[UUID]
    tipo: str
    recipient: str
    subject: Optional[str]
    status: str
    error_message: Optional[str]
    sent_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class SendNotificationRequest(BaseModel):
    channel_id: UUID
    recipient: str
    subject: Optional[str] = None
    body: str
    metadata: Optional[Dict[str, Any]] = None
