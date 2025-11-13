"""Schemas Pydantic para Compras"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# Base schema - Compra
class CompraBase(BaseModel):
    """Campos comunes de Compra"""

    numero: str = Field(..., max_length=50, description="Número de compra")
    proveedor_id: UUID | None = Field(None, description="ID del proveedor")
    fecha: date = Field(default_factory=date.today)
    subtotal: float = Field(default=0, ge=0)
    impuestos: float = Field(default=0, ge=0)
    total: float = Field(default=0, ge=0)
    estado: str = Field(default="draft", pattern="^(draft|confirmed|received|cancelled)$")
    notas: str | None = None


# Create schema
class CompraCreate(CompraBase):
    """Schema para crear compra"""

    pass


# Update schema
class CompraUpdate(BaseModel):
    """Schema para actualizar compra (todos campos opcionales)"""

    numero: str | None = Field(None, max_length=50)
    proveedor_id: UUID | None = None
    fecha: date | None = None
    subtotal: float | None = Field(None, ge=0)
    impuestos: float | None = Field(None, ge=0)
    total: float | None = Field(None, ge=0)
    estado: str | None = Field(None, pattern="^(draft|confirmed|received|cancelled)$")
    notas: str | None = None

    model_config = ConfigDict(extra="forbid")


# Response schema
class CompraResponse(CompraBase):
    """Schema de respuesta de compra"""

    id: UUID
    tenant_id: UUID
    usuario_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# List schema
class CompraList(BaseModel):
    """Schema para lista paginada de compras"""

    items: list[CompraResponse]
    total: int
    page: int = 1
    page_size: int = 100


# Base schema - CompraLinea
class CompraLineaBase(BaseModel):
    """Campos comunes de línea de compra"""

    producto_id: UUID = Field(..., description="ID del producto")
    cantidad: float = Field(..., gt=0, description="Cantidad")
    precio_unitario: float = Field(..., ge=0, description="Precio unitario")
    impuesto_tasa: float = Field(default=0, ge=0, le=1, description="Tasa de impuesto (0-1)")
    descuento: float = Field(default=0, ge=0, le=100, description="Descuento en %")
    total: float = Field(default=0, ge=0, description="Total de línea")


# Create schema
class CompraLineaCreate(CompraLineaBase):
    """Schema para crear línea de compra"""

    compra_id: UUID = Field(..., description="ID de la compra")


# Response schema
class CompraLineaResponse(CompraLineaBase):
    """Schema de respuesta de línea de compra"""

    id: UUID
    compra_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
