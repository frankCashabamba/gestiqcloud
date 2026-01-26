"""Module: schemas.py

Auto-generated module docstring."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ---------- MÓDULO ----------
class ModuloBase(BaseModel):
    """Module base schema (english only)."""

    name: str
    description: str | None = None
    active: bool
    icon: str | None = None
    url: str | None = None
    initial_template: str
    context_type: str | None = None
    target_model: str | None = None
    context_filters: dict | None = None
    category: str | None = None


class ModuloCreate(ModuloBase):
    """Class ModuloCreate - auto-generated docstring."""

    pass


class ModuloOut(ModuloBase):
    """Module output schema."""

    id: UUID

    model_config = ConfigDict(from_attributes=True)


# ---------- EMPRESA-MÓDULO ----------
class EmpresaModuloBase(BaseModel):
    """Company-module base schema (english only)."""

    module_id: UUID | str
    active: bool = True
    expiration_date: date | None = None
    initial_template: str | None = None


class EmpresaModuloCreate(EmpresaModuloBase):
    """Class EmpresaModuloCreate - auto-generated docstring."""

    pass


class EmpresaModuloOut(EmpresaModuloBase):
    """Company-module output schema."""

    id: UUID
    tenant_id: UUID
    company_slug: str | None
    activation_date: date | None = None
    module: ModuloOut | None = None

    model_config = ConfigDict(from_attributes=True)


# ---------- MÓDULO ASIGNADO A USUARIO ----------
class ModuloAsignadoBase(BaseModel):
    """Class ModuloAsignadoBase - auto-generated docstring."""

    modulo_id: UUID | str


class ModuloAsignadoCreate(ModuloAsignadoBase):
    """Class ModuloAsignadoCreate - auto-generated docstring."""

    usuario_id: int


class ModuloAsignadoOut(BaseModel):
    """Class ModuloAsignadoOut - auto-generated docstring."""

    id: UUID
    tenant_id: UUID
    usuario_id: int
    modulo_id: int
    fecha_asignacion: datetime
    modulo: ModuloBase | None  # ✅ necesario

    model_config = ConfigDict(from_attributes=True)


class EmpresaModuloOutAdmin(BaseModel):
    """Company-module output schema for admin."""

    id: UUID
    tenant_id: UUID
    module_id: UUID | int
    active: bool
    activation_date: date
    expiration_date: date | None
    initial_template: str | None
    company_slug: str | None
    module: ModuloOut | None = None

    model_config = ConfigDict(from_attributes=True)


class ModuloUpdate(BaseModel):
    """Schema used when updating a module."""

    name: str | None
    description: str | None
    icon: str | None
    url: str | None
    initial_template: str | None
    context_type: str | None
    target_model: str | None
    context_filters: dict | None
    category: str | None
    active: bool | None
