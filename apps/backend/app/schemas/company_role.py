"""Schemas for company roles management."""

from pydantic import BaseModel, Field


class RolEmpresaBase(BaseModel):
    """Base schema for company roles."""

    name: str = Field(..., min_length=1, max_length=100, description="Role name")
    description: str | None = Field(None, description="Role description")
    permissions: dict = Field(default_factory=dict, description="Role permissions (JSON structure)")


class RolEmpresaCreate(RolEmpresaBase):
    """Create company role."""


class RolEmpresaUpdate(BaseModel):
    """Update company role."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    permissions: dict | None = None


class RolEmpresaOut(RolEmpresaBase):
    """Company role response schema."""

    id: int
    tenant_id: int
    rol_base_id: int | None = None
    created_by_company: bool

    class Config:
        from_attributes = True
