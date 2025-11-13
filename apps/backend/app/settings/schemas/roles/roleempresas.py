"""Module: roleempresas.py

Auto-generated module docstring."""

# settings/schemas/roles/roleemresas.py
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class RolBase(BaseModel):
    """Class RolBase - auto-generated docstring."""

    nombre: str
    descripcion: Optional[str] = None
    permisos: Dict[str, bool] = {}


class RolCreate(BaseModel):
    """Class RolCreate - auto-generated docstring."""

    nombre: str
    descripcion: Optional[str]
    permisos: List[str]
    copiar_desde_id: Optional[int] = None


class RolUpdate(RolBase):
    """Class RolUpdate - auto-generated docstring."""

    pass


class RolResponse(RolBase):
    """Class RolResponse - auto-generated docstring."""

    id: int
    tenant_id: int
    creado_por_empresa: bool

    model_config = ConfigDict(from_attributes=True)


class RolEmpresaOut(BaseModel):
    """Class RolEmpresaOut - auto-generated docstring."""

    id: int
    nombre: str
    descripcion: Optional[str]
    permisos: Optional[Dict[str, bool]]

    model_config = ConfigDict(from_attributes=True)
