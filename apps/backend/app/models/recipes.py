"""
SQLAlchemy Models - Recipe System
"""

from sqlalchemy import (
    Boolean,
    Column,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.config.database import Base as BaseModel


class Recipe(BaseModel):
    """Production recipe."""

    __tablename__ = "recipes"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id = Column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(200), nullable=False)
    yield_qty = Column(Integer, nullable=False)  # units produced
    total_cost = Column(Numeric(12, 4), default=0)
    # Generated: CASE WHEN yield_qty > 0 THEN total_cost / yield_qty ELSE 0 END
    unit_cost = Column(
        Numeric(12, 4),
        Computed(
            text("CASE WHEN yield_qty > 0 THEN total_cost / yield_qty ELSE 0 END"),
            persisted=True,
        ),
    )
    prep_time_minutes = Column(Integer)  # minutes
    instructions = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    ingredients = relationship(
        "RecipeIngredient",
        back_populates="recipe",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    product = relationship("Product", foreign_keys=[product_id], back_populates="recipe")

    # Constraints
    __table_args__ = (
        Index("idx_recipes_tenant", "tenant_id"),
        Index("idx_recipes_product", "product_id"),
        Index("idx_recipes_is_active", "is_active", postgresql_where=text("is_active = TRUE")),
        {"extend_existing": True},
    )

    def __repr__(self):
        return f"<Recipe {self.name} (yield: {self.yield_qty})>"


class RecipeIngredient(BaseModel):
    """Recipe ingredient with purchase info."""

    __tablename__ = "recipe_ingredients"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    recipe_id = Column(
        UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False
    )
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )

    qty = Column(Numeric(12, 4), nullable=False)
    unit = Column(String(10), nullable=False)

    purchase_packaging = Column(String(100))  # e.g. "Bag 110 lbs"
    qty_per_package = Column(Numeric(12, 4), nullable=False)
    package_unit = Column(String(10), nullable=False)
    package_cost = Column(Numeric(12, 4), nullable=False)
    ingredient_cost = Column(
        Numeric(12, 4),
        Computed(
            text(
                "CASE WHEN qty_per_package > 0 THEN (qty * package_cost) / qty_per_package ELSE 0 END"
            ),
            persisted=True,
        ),
    )

    notes = Column(Text)
    line_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    recipe = relationship("Recipe", back_populates="ingredients")
    product = relationship(
        "Product", foreign_keys=[product_id], back_populates="used_in_ingredients"
    )

    # Constraints
    __table_args__ = (
        Index("idx_recipe_ingredients_recipe", "recipe_id"),
        Index("idx_recipe_ingredients_product", "product_id"),
        {"extend_existing": True},
    )

    def __repr__(self):
        return f"<RecipeIngredient {self.qty} {self.unit}>"
