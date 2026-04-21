"""Module: product_category.py

Product category model for organizing products."""

import uuid
from typing import Optional

from sqlalchemy import JSON, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseCatalogModel
from app.models.tenant import Tenant

# JSONB with SQLite fallback
JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class ProductCategory(BaseCatalogModel):
    """Product category with multi-tenant isolation and hierarchical support."""

    __tablename__ = "product_categories"
    __table_args__ = {"extend_existing": True}

    # Additional fields specific to ProductCategory
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    category_metadata: Mapped[dict | None] = mapped_column(JSON_TYPE, nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship()
    parent: Mapped[Optional["ProductCategory"]] = relationship(
        remote_side=[id], back_populates="children"
    )
    children: Mapped[list["ProductCategory"]] = relationship(back_populates="parent")

    def __repr__(self):
        return f"<ProductCategory(id={self.id}, name='{self.name}', tenant_id={self.tenant_id})>"
