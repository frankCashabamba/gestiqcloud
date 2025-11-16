"""
Base schemas and common types for consistent UUID usage across the application.
"""

from uuid import UUID
from pydantic import BaseModel, ConfigDict


class UUIDBase(BaseModel):
    """Base model with UUID field for all entities."""

    id: UUID

    model_config = ConfigDict(from_attributes=True)


class TenantMixin(BaseModel):
    """Mixin for entities that belong to a tenant."""

    tenant_id: UUID

    model_config = ConfigDict(from_attributes=True)


class BaseEntity(UUIDBase, TenantMixin):
    """Base entity with both ID and tenant_id as UUID."""

    model_config = ConfigDict(from_attributes=True)
