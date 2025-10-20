"""Module: products.py

Auto-generated module docstring."""

import uuid
from typing import List, Optional

from sqlalchemy import JSON, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base
from app.models.tenant import Tenant


class Product(Base):
    """ Class Product - auto-generated docstring. """
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    sku: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    name: Mapped[str] = mapped_column(String, index=True)
    price: Mapped[float] = mapped_column(Float)
    stock: Mapped[float] = mapped_column(Float, default=0)
    unit: Mapped[str] = mapped_column(String, default="unidad")
    product_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))

    tenant: Mapped["Tenant"] = relationship()

    # Relación uno a uno (este producto tiene UNA receta asociada)
    recipe: Mapped[Optional["Recipe"]] = relationship(back_populates="product", uselist=False)

    # Este producto puede estar en muchos ingredientes de recetas
    used_in_ingredients: Mapped[List["RecipeIngredient"]] = relationship(back_populates="product")


class Recipe(Base):
    """ Class Recipe - auto-generated docstring. """
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    yield_quantity: Mapped[float] = mapped_column(Float)

    product: Mapped["Product"] = relationship(back_populates="recipe")

    ingredients: Mapped[List["RecipeIngredient"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan"
    )


class RecipeIngredient(Base):
    """ Class RecipeIngredient - auto-generated docstring. """
    __tablename__ = "recipe_ingredients"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String)

    recipe: Mapped["Recipe"] = relationship(back_populates="ingredients")
    product: Mapped["Product"] = relationship(back_populates="used_in_ingredients")
