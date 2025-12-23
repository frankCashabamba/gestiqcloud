"""Module: configuration.py

Auto-generated module docstring."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CompanyCategoryBase(BaseModel):
    """
    DEPRECATED: Use BusinessCategory instead.

    Base schema for company categories. Keep for backward compatibility only.
    """

    name: str


class CompanyCategoryCreate(CompanyCategoryBase):
    """
    DEPRECATED: Use BusinessCategory instead.

    Schema for creating company categories. Keep for backward compatibility only.
    """

    pass


class CompanyCategory(CompanyCategoryBase):
    """
    DEPRECATED: Use BusinessCategory instead.

    Schema for company categories. Keep for backward compatibility only.
    Will be removed in Q1 2026.
    """

    id: int
    model_config = ConfigDict(from_attributes=True)


# DEPRECATED Aliases for backward compatibility (Spanish naming)
CategoriaEmpresaBase = CompanyCategoryBase
CategoriaEmpresaCreate = CompanyCategoryCreate
CategoriaEmpresa = CompanyCategory


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
