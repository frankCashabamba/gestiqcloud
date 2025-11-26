"""Schemas for company roles management."""

from pydantic import BaseModel, ConfigDict, Field


class CompanyRoleBase(BaseModel):
    """Base schema for company roles."""

    name: str = Field(..., min_length=1, max_length=100, description="Role name")
    description: str | None = Field(None, description="Role description")
    permissions: dict = Field(default_factory=dict, description="Role permissions (JSON structure)")


class CompanyRoleCreate(CompanyRoleBase):
    """Create company role."""


class CompanyRoleUpdate(BaseModel):
    """Update company role."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    permissions: dict | None = None


class CompanyRoleOut(CompanyRoleBase):
    """Company role response schema."""

    id: int
    tenant_id: int
    rol_base_id: int | None = None
    created_by_company: bool

    model_config = ConfigDict(from_attributes=True)
