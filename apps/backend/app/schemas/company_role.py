"""Schemas for company roles management."""

from typing import Literal
from uuid import UUID

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

    id: UUID
    tenant_id: UUID
    base_role_id: UUID | None = None
    created_by_company: bool

    model_config = ConfigDict(from_attributes=True)


class CompanyRoleSeedEntry(BaseModel):
    """Role created or reused from an operational preset."""

    role: CompanyRoleOut
    status: Literal["created", "existing"]


class CompanyRoleSeedSummary(BaseModel):
    """Summary of operational role seeding."""

    template: str
    sector: str | None = None
    created: int = 0
    existing: int = 0
    items: list[CompanyRoleSeedEntry] = Field(default_factory=list)
