"""Schemas for company roles (settings layer)."""

from pydantic import BaseModel, ConfigDict


class RolBase(BaseModel):
    """Base role schema."""

    name: str
    description: str | None = None
    permissions: dict[str, bool] = {}


class RolCreate(BaseModel):
    """Create role schema."""

    name: str
    description: str | None
    permissions: list[str]
    copy_from_id: int | None = None


class RolUpdate(RolBase):
    """Update role schema."""


class RolResponse(RolBase):
    """Role response schema."""

    id: int
    tenant_id: int
    created_by_company: bool

    model_config = ConfigDict(from_attributes=True)


class RolEmpresaOut(BaseModel):
    """Company role output schema."""

    id: int
    name: str
    description: str | None
    permissions: dict[str, bool] | None

    model_config = ConfigDict(from_attributes=True)
