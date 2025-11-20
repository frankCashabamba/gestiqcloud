"""Schemas para gestión de roles de empresa."""

from pydantic import BaseModel, Field


class RolEmpresaBase(BaseModel):
    """Base schema para roles de empresa."""

    name: str = Field(..., min_length=1, max_length=100, description="Nombre del rol")
    description: str | None = Field(None, description="Descripción del rol")
    permissions: dict = Field(default_factory=dict, description="Permisos del rol en formato JSON")


class RolEmpresaCreate(RolEmpresaBase):
    """Schema para crear un rol de empresa."""

    pass


class RolEmpresaUpdate(BaseModel):
    """Schema para actualizar un rol de empresa."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    permissions: dict | None = None


class RolEmpresaOut(RolEmpresaBase):
    """Schema de salida para roles de empresa."""

    id: int
    tenant_id: int
    rol_base_id: int | None = None
    created_by_company: bool

    class Config:
        from_attributes = True
