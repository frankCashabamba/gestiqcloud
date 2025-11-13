"""Module: roleempresas.py

Auto-generated module docstring."""

# settings/schemas/roles/roleemresas.py

from pydantic import BaseModel, ConfigDict


class RolBase(BaseModel):
    """Class RolBase - auto-generated docstring."""

    nombre: str
    descripcion: str | None = None
    permisos: dict[str, bool] = {}


class RolCreate(BaseModel):
    """Class RolCreate - auto-generated docstring."""

    nombre: str
    descripcion: str | None
    permisos: list[str]
    copiar_desde_id: int | None = None


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
    descripcion: str | None
    permisos: dict[str, bool] | None

    model_config = ConfigDict(from_attributes=True)
