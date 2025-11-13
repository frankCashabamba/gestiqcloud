"""Schemas Pydantic para Ventas"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# Base schema
class VentaBase(BaseModel):
    """Campos comunes de Venta"""

    numero: str = Field(..., max_length=50, description="Número de venta")
    cliente_id: UUID | None = Field(None, description="ID del cliente")
    fecha: date = Field(default_factory=date.today)
    subtotal: float = Field(default=0, ge=0)
    impuestos: float = Field(default=0, ge=0)
    total: float = Field(default=0, ge=0)
    estado: str = Field(default="draft", pattern="^(draft|confirmed|invoiced|cancelled)$")
    notas: str | None = None


# Create schema
class VentaCreate(VentaBase):
    """Schema para crear venta"""

    pass


# Update schema
class VentaUpdate(BaseModel):
    """Schema para actualizar venta (todos campos opcionales)"""

    numero: str | None = Field(None, max_length=50)
    cliente_id: UUID | None = None
    fecha: date | None = None
    subtotal: float | None = Field(None, ge=0)
    impuestos: float | None = Field(None, ge=0)
    total: float | None = Field(None, ge=0)
    estado: str | None = Field(None, pattern="^(draft|confirmed|invoiced|cancelled)$")
    notas: str | None = None

    model_config = ConfigDict(extra="forbid")


# Response schema
class VentaResponse(VentaBase):
    """Schema de respuesta de venta"""

    id: UUID
    tenant_id: UUID
    usuario_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# List schema
class VentaList(BaseModel):
    """Schema para lista paginada de ventas"""

    items: list[VentaResponse]
    total: int
    page: int = 1
    page_size: int = 100
