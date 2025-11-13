"""Schemas Pydantic para Gastos"""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# Base schema
class GastoBase(BaseModel):
    """Campos comunes de Gasto"""

    numero: str = Field(..., max_length=50, description="Número de gasto")
    proveedor_id: Optional[UUID] = Field(None, description="ID del proveedor")
    categoria_gasto_id: Optional[UUID] = Field(
        None, description="ID de categoría de gasto"
    )
    fecha: date = Field(default_factory=date.today)
    concepto: str = Field(..., max_length=255, description="Concepto del gasto")
    subtotal: float = Field(default=0, ge=0)
    impuestos: float = Field(default=0, ge=0)
    total: float = Field(default=0, ge=0)
    estado: str = Field(default="draft", pattern="^(draft|approved|paid|cancelled)$")
    metodo_pago: Optional[str] = Field(None, pattern="^(cash|card|transfer|check)$")
    referencia: Optional[str] = Field(
        None, max_length=100, description="Referencia bancaria o cheque"
    )
    notas: Optional[str] = None


# Create schema
class GastoCreate(GastoBase):
    """Schema para crear gasto"""

    pass


# Update schema
class GastoUpdate(BaseModel):
    """Schema para actualizar gasto (todos campos opcionales)"""

    numero: Optional[str] = Field(None, max_length=50)
    proveedor_id: Optional[UUID] = None
    categoria_gasto_id: Optional[UUID] = None
    fecha: Optional[date] = None
    concepto: Optional[str] = Field(None, max_length=255)
    subtotal: Optional[float] = Field(None, ge=0)
    impuestos: Optional[float] = Field(None, ge=0)
    total: Optional[float] = Field(None, ge=0)
    estado: Optional[str] = Field(None, pattern="^(draft|approved|paid|cancelled)$")
    metodo_pago: Optional[str] = Field(None, pattern="^(cash|card|transfer|check)$")
    referencia: Optional[str] = Field(None, max_length=100)
    notas: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


# Response schema
class GastoResponse(GastoBase):
    """Schema de respuesta de gasto"""

    id: UUID
    tenant_id: UUID
    usuario_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# List schema
class GastoList(BaseModel):
    """Schema para lista paginada de gastos"""

    items: list[GastoResponse]
    total: int
    page: int = 1
    page_size: int = 100
