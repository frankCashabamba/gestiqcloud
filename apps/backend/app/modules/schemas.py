"""Module: schemas.py

Auto-generated module docstring."""

from datetime import date, datetime
from typing import Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ---------- MÓDULO ----------
class ModuloBase(BaseModel):
    """Class ModuloBase - auto-generated docstring."""

    name: str
    description: Optional[str] = None
    active: bool
    icono: Optional[str] = "📦"
    url: Optional[str]
    plantilla_inicial: str
    context_type: Optional[str]
    modelo_objetivo: Optional[str]
    filtros_contexto: Optional[dict]
    categoria: Optional[str]


class ModuloCreate(ModuloBase):
    """Class ModuloCreate - auto-generated docstring."""

    pass


class ModuloOut(ModuloBase):
    """Class ModuloOut - auto-generated docstring."""

    id: int
    name: str
    active: bool

    model_config = ConfigDict(from_attributes=True)


# ---------- EMPRESA-MÓDULO ----------
class EmpresaModuloBase(BaseModel):
    """Class EmpresaModuloBase - auto-generated docstring."""

    modulo_id: int
    active: bool = True
    fecha_expiracion: Optional[date] = None
    plantilla_inicial: Optional[str] = None


class EmpresaModuloCreate(EmpresaModuloBase):
    """Class EmpresaModuloCreate - auto-generated docstring."""

    pass


class EmpresaModuloOut(EmpresaModuloBase):
    """Class EmpresaModuloOut - auto-generated docstring."""

    id: int
    tenant_id: UUID
    empresa_slug: Optional[str]
    active: bool
    fecha_expiracion: Optional[date] = None
    fecha_activacion: Optional[date] = None
    plantilla_inicial: Optional[str] = None

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

    id: int
    tenant_id: UUID
    usuario_id: int
    modulo_id: int
    fecha_asignacion: datetime
    modulo: Optional[ModuloBase]  # ✅ necesario

    model_config = ConfigDict(from_attributes=True)


class EmpresaModuloOutAdmin(BaseModel):
    """Class EmpresaModuloOutAdmin - auto-generated docstring."""

    id: int
    tenant_id: UUID
    modulo_id: int
    active: bool
    fecha_activacion: date
    fecha_expiracion: Optional[date]
    plantilla_inicial: Optional[str]
    empresa_slug: Optional[str]
    modulo: ModuloOut

    model_config = ConfigDict(from_attributes=True)


class ModuloUpdate(BaseModel):
    """Class ModuloUpdate - auto-generated docstring."""

    name: Optional[str]
    description: Optional[str]
    icono: Optional[str]
    url: Optional[str]
    plantilla_inicial: Optional[str]
    context_type: Optional[str]
    modelo_objetivo: Optional[str]
    filtros_contexto: Optional[Dict]
    categoria: Optional[str]
    active: Optional[bool]
