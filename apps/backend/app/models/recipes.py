"""
SQLAlchemy Models - Sistema de Recetas
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
    """Receta de producción"""

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
    rendimiento = Column(Integer, nullable=False)  # unidades producidas
    costo_total = Column(Numeric(12, 4), default=0)
    # Columna generada en BD: CASE WHEN rendimiento > 0 THEN costo_total / rendimiento ELSE 0 END
    costo_por_unidad = Column(
        Numeric(12, 4),
        Computed(
            text("CASE WHEN rendimiento > 0 THEN costo_total / rendimiento ELSE 0 END"),
            persisted=True,
        ),
    )
    tiempo_preparacion = Column(Integer)  # minutos
    instrucciones = Column(Text)
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    ingredientes = relationship(
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
        Index("idx_recipes_activo", "activo", postgresql_where=text("activo = TRUE")),
        {"extend_existing": True},
    )

    def __repr__(self):
        return f"<Recipe {self.name} (rend: {self.rendimiento})>"


class RecipeIngredient(BaseModel):
    """Ingrediente de receta con info de compra"""

    __tablename__ = "recipe_ingredients"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    recipe_id = Column(
        UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False
    )
    producto_id = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )

    qty = Column(Numeric(12, 4), nullable=False)
    unidad_medida = Column(String(10), nullable=False)

    # Info de presentación de compra
    presentacion_compra = Column(String(100))  # "Saco 110 lbs"
    qty_presentacion = Column(Numeric(12, 4), nullable=False)
    unidad_presentacion = Column(String(10), nullable=False)
    costo_presentacion = Column(Numeric(12, 4), nullable=False)
    # Columna generada en BD: CASE WHEN qty_presentacion > 0 THEN (qty * costo_presentacion) / qty_presentacion ELSE 0 END
    costo_ingrediente = Column(
        Numeric(12, 4),
        Computed(
            text(
                "CASE WHEN qty_presentacion > 0 THEN (qty * costo_presentacion) / qty_presentacion ELSE 0 END"
            ),
            persisted=True,
        ),
    )

    notas = Column(Text)
    orden = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    recipe = relationship("Recipe", back_populates="ingredientes")
    product = relationship(
        "Product", foreign_keys=[producto_id], back_populates="used_in_ingredients"
    )

    # Constraints
    __table_args__ = (
        Index("idx_recipe_ingredients_recipe", "recipe_id"),
        Index("idx_recipe_ingredients_producto", "producto_id"),
        {"extend_existing": True},
    )

    def __repr__(self):
        return f"<RecipeIngredient {self.qty} {self.unidad_medida}>"
