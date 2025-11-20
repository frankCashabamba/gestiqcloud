"""Module: configuracion.py

Auto-generated module docstring."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CategoriaEmpresaBase(BaseModel):
    """Class CategoriaEmpresaBase - auto-generated docstring."""

    name: str


class CategoriaEmpresaCreate(CategoriaEmpresaBase):
    """Class CategoriaEmpresaCreate - auto-generated docstring."""

    pass


class CategoriaEmpresa(CategoriaEmpresaBase):
    """Class CategoriaEmpresa - auto-generated docstring."""

    id: int
    model_config = ConfigDict(from_attributes=True)


# para roles
class RolBaseBase(BaseModel):
    """Class RolBaseBase - auto-generated docstring."""

    name: str
    description: str | None = ""
    permisos: list[str] = []


class RolBaseCreate(RolBaseBase):
    """Class RolBaseCreate - auto-generated docstring."""

    pass


class RolBaseUpdate(RolBaseBase):
    """Class RolBaseUpdate - auto-generated docstring."""

    permisos: list[str]


class RolBase(RolBaseBase):
    """Class RolBase - auto-generated docstring."""

    id: int
    model_config = ConfigDict(from_attributes=True)


class PermisoAccionGlobalpermiso(BaseModel):
    """Class PermisoAccionGlobalpermiso - auto-generated docstring."""

    id: int
    clave: str
    description: str | None
    model_config = ConfigDict(from_attributes=True)


class AuthenticatedUser(BaseModel):
    """Class AuthenticatedUser - auto-generated docstring."""

    user_id: UUID
    is_superadmin: bool
    user_type: str
    tenant_id: UUID | None = None
    empresa_slug: str | None = None
    plantilla: str | None = None
    es_admin_empresa: bool | None = None
    permisos: dict | None = {}
    name: str | None = None

    model_config = ConfigDict(extra="ignore")
