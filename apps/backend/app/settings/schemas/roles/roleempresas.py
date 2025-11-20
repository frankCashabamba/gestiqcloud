"""Module: roleempresas.py

Auto-generated module docstring."""

# settings/schemas/roles/roleemresas.py

from pydantic import BaseModel, ConfigDict


class RolBase(BaseModel):
    """Class RolBase - auto-generated docstring."""

    name: str
    description: str | None = None
    permissions: dict[str, bool] = {}


class RolCreate(BaseModel):
    """Class RolCreate - auto-generated docstring."""

    name: str
    description: str | None
    permissions: list[str]
    copy_from_id: int | None = None


class RolUpdate(RolBase):
    """Class RolUpdate - auto-generated docstring."""

    pass


class RolResponse(RolBase):
    """Class RolResponse - auto-generated docstring."""

    id: int
    tenant_id: int
    created_by_company: bool

    model_config = ConfigDict(from_attributes=True)


class RolEmpresaOut(BaseModel):
    """Class RolEmpresaOut - auto-generated docstring."""

    id: int
    name: str
    description: str | None
    permissions: dict[str, bool] | None

    model_config = ConfigDict(from_attributes=True)
