"""
Schemas Pydantic para notificaciones
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid


# ============================================================================
# NOTIFICATION CHANNELS
# ============================================================================


class NotificationChannelBase(BaseModel):
    tipo: str = Field(..., description="Tipo: email, whatsapp, telegram")
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    config: Dict[str, Any] = Field(
        ..., description="Configuración específica del canal"
    )
    active: bool = True
    use_for_alerts: bool = True
    use_for_invoices: bool = False
    use_for_marketing: bool = False


class NotificationChannelCreate(NotificationChannelBase):
    pass


class NotificationChannelUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    active: Optional[bool] = None
    use_for_alerts: Optional[bool] = None
    use_for_invoices: Optional[bool] = None
    use_for_marketing: Optional[bool] = None


class NotificationChannelResponse(NotificationChannelBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# ============================================================================
# NOTIFICATION LOGS
# ============================================================================


class NotificationLogResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    tipo: str
    canal: Optional[str]
    destinatario: str
    asunto: Optional[str]
    mensaje: str
    estado: str
    extra_data: Optional[Dict[str, Any]]
    error_message: Optional[str]
    ref_type: Optional[str]
    ref_id: Optional[uuid.UUID]
    sent_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# STOCK ALERTS
# ============================================================================


class StockAlertResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    product_id: uuid.UUID
    warehouse_id: Optional[uuid.UUID]
    nivel_actual: int
    nivel_minimo: int
    diferencia: int
    estado: str
    notified_at: Optional[datetime]
    notified_via: Optional[List[str]]
    resolved_at: Optional[datetime]
    resolved_by: Optional[uuid.UUID]
    created_at: datetime

    class Config:
        from_attributes = True


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

    channel_id: Optional[uuid.UUID] = None
    config_override: Optional[Dict[str, Any]] = None

    ref_type: Optional[str] = None
    ref_id: Optional[uuid.UUID] = None

    @validator("tipo")
    def validate_tipo(cls, v):
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
    asunto_template: Optional[str] = Field(None, max_length=500)
    mensaje_template: str
    variables: Dict[str, str] = Field(default={}, description="Variables disponibles")
    active: bool = True


class NotificationTemplateCreate(NotificationTemplateBase):
    pass


class NotificationTemplateResponse(NotificationTemplateBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
