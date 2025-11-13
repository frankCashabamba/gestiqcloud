"""Schemas Pydantic para Proveedores"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ProveedorContactoCreate(BaseModel):
    """Schema para crear contacto de proveedor"""

    name: str = Field(..., max_length=255)
    cargo: str | None = Field(None, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)


class ProveedorContactoResponse(ProveedorContactoCreate):
    """Schema de respuesta de contacto"""

    id: UUID
    proveedor_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProveedorDireccionCreate(BaseModel):
    """Schema para crear dirección de proveedor"""

    tipo: str | None = Field(None, pattern="^(fiscal|envio|otro)$")
    address: str | None = None
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    codigo_postal: str | None = Field(None, max_length=20)
    pais: str = Field(default="ES", max_length=2)


class ProveedorDireccionResponse(ProveedorDireccionCreate):
    """Schema de respuesta de dirección"""

    id: UUID
    proveedor_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProveedorBase(BaseModel):
    """Campos comunes de Proveedor"""

    codigo: str | None = Field(None, max_length=50)
    name: str = Field(..., max_length=255)
    nombre_comercial: str | None = Field(None, max_length=255)
    tax_id: str | None = Field(None, max_length=50)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)
    web: str | None = Field(None, max_length=255)
    active: bool = True
    notas: str | None = None


class ProveedorCreate(ProveedorBase):
    """Schema para crear proveedor"""

    contactos: list[ProveedorContactoCreate] = Field(default_factory=list)
    direcciones: list[ProveedorDireccionCreate] = Field(default_factory=list)


class ProveedorUpdate(BaseModel):
    """Schema para actualizar proveedor"""

    codigo: str | None = Field(None, max_length=50)
    name: str | None = Field(None, max_length=255)
    nombre_comercial: str | None = Field(None, max_length=255)
    tax_id: str | None = Field(None, max_length=50)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)
    web: str | None = Field(None, max_length=255)
    active: bool | None = None
    notas: str | None = None

    model_config = ConfigDict(extra="forbid")


class ProveedorResponse(ProveedorBase):
    """Schema de respuesta de proveedor"""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    contactos: list[ProveedorContactoResponse] = Field(default_factory=list)
    direcciones: list[ProveedorDireccionResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ProveedorList(BaseModel):
    """Schema para lista paginada de proveedores"""

    items: list[ProveedorResponse]
    total: int
    page: int = 1
    page_size: int = 100
