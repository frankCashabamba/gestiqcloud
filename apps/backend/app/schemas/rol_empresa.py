"""Schemas para gestión de roles de empresa."""

from typing import Optional
from pydantic import BaseModel, Field


class RolEmpresaBase(BaseModel):
    """Base schema para roles de empresa."""

    name: str = Field(..., min_length=1, max_length=100, description="Nombre del rol")
    description: Optional[str] = Field(None, description="Descripción del rol")
    permisos: dict = Field(
        default_factory=dict, description="Permisos del rol en formato JSON"
    )


class RolEmpresaCreate(RolEmpresaBase):
    """Schema para crear un rol de empresa."""

    pass


class RolEmpresaUpdate(BaseModel):
    """Schema para actualizar un rol de empresa."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    permisos: Optional[dict] = None


class RolEmpresaOut(RolEmpresaBase):
    """Schema de salida para roles de empresa."""

    id: int
    tenant_id: int
    rol_base_id: Optional[int] = None
    creado_por_empresa: bool

    class Config:
        from_attributes = True
