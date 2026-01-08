"""Module: products.py

Auto-generated module docstring."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.config.database import Base
from app.models.tenant import Tenant


class Product(Base):
    """Product model - MODERN schema (English names)"""

    __tablename__ = "products"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    cost_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    tax_rate: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True, default=None)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    stock: Mapped[float] = mapped_column(Float, default=0)
    unit: Mapped[str] = mapped_column(Text, default="unit")
    product_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("product_categories.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    tenant: Mapped["Tenant"] = relationship()
    category_rel = relationship("ProductCategory", foreign_keys=[category_id], lazy="select")
    recipe: Mapped[Optional["Recipe"]] = relationship(  # noqa: F821
        back_populates="product", uselist=False
    )
    used_in_ingredients: Mapped[list["RecipeIngredient"]] = relationship(  # noqa: F821
        back_populates="product"
    )

    @property
    def category(self) -> str | None:
        rel = self.category_rel
        return rel.name if rel else None

    @property
    def categoria(self) -> str | None:
        return self.category


# Recipe and RecipeIngredient models moved to app.models.recipes
# Import from there instead: from app.models.recipes import Recipe, RecipeIngredient
