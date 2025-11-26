"""Module: configuration.py

Auto-generated module docstring."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CompanyCategoryBase(BaseModel):
    """Class CompanyCategoryBase - auto-generated docstring."""

    name: str


class CompanyCategoryCreate(CompanyCategoryBase):
    """Class CompanyCategoryCreate - auto-generated docstring."""

    pass


class CompanyCategory(CompanyCategoryBase):
    """Class CompanyCategory - auto-generated docstring."""

    id: int
    model_config = ConfigDict(from_attributes=True)


# Role schemas
class RolBaseBase(BaseModel):
    """Class RolBaseBase - auto-generated docstring."""

    name: str
    description: str | None = ""
    permissions: list[str] = []


class RolBaseCreate(RolBaseBase):
    """Class RolBaseCreate - auto-generated docstring."""

    pass


class RolBaseUpdate(RolBaseBase):
    """Class RolBaseUpdate - auto-generated docstring."""

    permissions: list[str]


class RolBase(RolBaseBase):
    """Class RolBase - auto-generated docstring."""

    id: int
    model_config = ConfigDict(from_attributes=True)


class GlobalActionPermissionSchema(BaseModel):
    """Class GlobalActionPermissionSchema - auto-generated docstring."""

    id: int
    key: str
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
    is_company_admin: bool | None = None
    permisos: dict | None = {}
    name: str | None = None

    model_config = ConfigDict(extra="ignore")
