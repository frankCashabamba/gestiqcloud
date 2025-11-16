"""Module: schemas.py

Auto-generated module docstring."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ---------- MÓDULO ----------
class ModuloBase(BaseModel):
    """Class ModuloBase - auto-generated docstring."""

    name: str
    description: str | None = None
    active: bool
    icono: str | None = "📦"
    url: str | None
    plantilla_inicial: str
    context_type: str | None
    modelo_objetivo: str | None
    filtros_contexto: dict | None
    categoria: str | None


class ModuloCreate(ModuloBase):
    """Class ModuloCreate - auto-generated docstring."""

    pass


class ModuloOut(ModuloBase):
    """Class ModuloOut - auto-generated docstring."""

    id: UUID
    name: str
    active: bool

    model_config = ConfigDict(from_attributes=True)


# ---------- EMPRESA-MÓDULO ----------
class EmpresaModuloBase(BaseModel):
    """Class EmpresaModuloBase - auto-generated docstring."""

    modulo_id: int
    active: bool = True
    fecha_expiracion: date | None = None
    plantilla_inicial: str | None = None


class EmpresaModuloCreate(EmpresaModuloBase):
    """Class EmpresaModuloCreate - auto-generated docstring."""

    pass


class EmpresaModuloOut(EmpresaModuloBase):
    """Class EmpresaModuloOut - auto-generated docstring."""

    id: UUID
    tenant_id: UUID
    empresa_slug: str | None
    active: bool
    fecha_expiracion: date | None = None
    fecha_activacion: date | None = None
    plantilla_inicial: str | None = None

    modulo: ModuloOut

    model_config = ConfigDict(from_attributes=True)


# ---------- MÓDULO ASIGNADO A USUARIO ----------
class ModuloAsignadoBase(BaseModel):
    """Class ModuloAsignadoBase - auto-generated docstring."""

    modulo_id: int


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
    """Class EmpresaModuloOutAdmin - auto-generated docstring."""

    id: UUID
    tenant_id: UUID
    modulo_id: int
    active: bool
    fecha_activacion: date
    fecha_expiracion: date | None
    plantilla_inicial: str | None
    empresa_slug: str | None
    modulo: ModuloOut

    model_config = ConfigDict(from_attributes=True)


class ModuloUpdate(BaseModel):
    """Class ModuloUpdate - auto-generated docstring."""

    name: str | None
    description: str | None
    icono: str | None
    url: str | None
    plantilla_inicial: str | None
    context_type: str | None
    modelo_objetivo: str | None
    filtros_contexto: dict | None
    categoria: str | None
    active: bool | None
