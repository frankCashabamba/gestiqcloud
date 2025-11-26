"""
Schemas Pydantic para notificaciones
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ============================================================================
# NOTIFICATION CHANNELS
# ============================================================================


class NotificationChannelBase(BaseModel):
    tipo: str = Field(..., description="Tipo: email, whatsapp, telegram")
    name: str = Field(..., max_length=100)
    description: str | None = None
    config: dict[str, Any] = Field(..., description="Configuración específica del canal")
    active: bool = True
    use_for_alerts: bool = True
    use_for_invoices: bool = False
    use_for_marketing: bool = False


class NotificationChannelCreate(NotificationChannelBase):
    pass


class NotificationChannelUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    description: str | None = None
    config: dict[str, Any] | None = None
    active: bool | None = None
    use_for_alerts: bool | None = None
    use_for_invoices: bool | None = None
    use_for_marketing: bool | None = None


class NotificationChannelResponse(NotificationChannelBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# NOTIFICATION LOGS
# ============================================================================


class NotificationLogResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    tipo: str
    canal: str | None
    destinatario: str
    asunto: str | None
    mensaje: str
    estado: str
    extra_data: dict[str, Any] | None
    error_message: str | None
    ref_type: str | None
    ref_id: uuid.UUID | None
    sent_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# STOCK ALERTS
# ============================================================================


class StockAlertResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    product_id: uuid.UUID
    warehouse_id: uuid.UUID | None
    nivel_actual: int
    nivel_minimo: int
    diferencia: int
    estado: str
    notified_at: datetime | None
    notified_via: list[str] | None
    resolved_at: datetime | None
    resolved_by: uuid.UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# REQUESTS
# ============================================================================


class NotificationTestRequest(BaseModel):
    channel_id: uuid.UUID = Field(..., description="Canal a probar")
    destinatario: str = Field(..., description="Email/phone/chat_id de prueba")


class NotificationSendRequest(BaseModel):
    tipo: str = Field(..., description="email, whatsapp, telegram")
    destinatario: str = Field(..., description="Email/phone/chat_id")
    asunto: str = Field(..., max_length=500)
    mensaje: str = Field(..., description="Cuerpo del mensaje (HTML para email)")

    channel_id: uuid.UUID | None = None
    config_override: dict[str, Any] | None = None

    ref_type: str | None = None
    ref_id: uuid.UUID | None = None

    @field_validator("tipo")
    def validate_tipo(cls, v: str):
        if v not in ["email", "whatsapp", "telegram"]:
            raise ValueError("tipo debe ser: email, whatsapp o telegram")
        return v


# ============================================================================
# TEMPLATES (Futuro)
# ============================================================================


class NotificationTemplateBase(BaseModel):
    codigo: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    tipo: str
    asunto_template: str | None = Field(None, max_length=500)
    mensaje_template: str
    variables: dict[str, str] = Field(default={}, description="Variables disponibles")
    active: bool = True


class NotificationTemplateCreate(NotificationTemplateBase):
    pass


class NotificationTemplateResponse(NotificationTemplateBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
