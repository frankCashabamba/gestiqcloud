"""
Recipe Steps Model - Desglose de etapas en recetas para costeo detallado.

Permite separar una receta en etapas estándar reutilizables,
cada una con su tipo de recurso (labor, oven, mixer, etc).
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.config.database import Base as BaseModel


class RecipeStep(BaseModel):
    """
    Etapa dentro de una receta.
    
    Permite desglosar una receta en pasos estándar, cada uno con:
    - Duración
    - Si requiere atención del operario (is_touch)
    - Tipo de recurso que consume (labor, oven, mixer, etc)
    
    Ejemplo:
        Receta "Pan Integral" → 8 pasos:
        1. Pesar/mise en place (10 min, TOUCH, LABOR)
        2. Amasado (5 min, TOUCH, LABOR)
        3. Reposo 1 (45 min, NO TOUCH, FERMENTATION)
        4. Boleo/formado (40 min, TOUCH, LABOR)
        5. Fermentación final (90 min, NO TOUCH, FERMENTATION)
        6. Horneado (25 min, NO TOUCH, OVEN)
        7. Cargar/descargar (10 min, TOUCH, LABOR)
        8. Empaque (5 min, TOUCH, LABOR)
    """

    __tablename__ = "recipe_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    recipe_id = Column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Contenido de la etapa
    step_name = Column(
        String(100),
        nullable=False,
        comment="Nombre: 'Pesar/mise en place', 'Amasado', 'Fermentación', etc"
    )
    description = Column(Text, nullable=True)
    duration_minutes = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Duración estándar en minutos"
    )
    
    # Clasificación de trabajo
    is_touch = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="TRUE: operario está activamente ocupado (cuesta mano de obra). FALSE: proceso pasivo"
    )
    
    # Tipo de recurso consumido
    resource_type = Column(
        String(20),
        nullable=False,
        default="labor",
        comment="Tipo de recurso: labor, oven, mixer, prover, other"
    )
    
    # Datos opcionales para costos reales
    actual_minutes = Column(
        Integer,
        nullable=True,
        comment="Duración real medida (si se registra en producción)"
    )
    
    # Ordenamiento y control
    step_order = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Orden de ejecución en la receta (0-based)"
    )
    is_active = Column(Boolean, default=True)
    
    # Auditoría
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    recipe = relationship("Recipe", foreign_keys=[recipe_id])

    # Constraints
    __table_args__ = (
        Index("idx_recipe_steps_recipe_id", "recipe_id"),
        Index("idx_recipe_steps_is_touch", "is_touch"),
        Index("idx_recipe_steps_resource_type", "resource_type"),
        {"extend_existing": True},
    )

    def __repr__(self):
        return f"<RecipeStep {self.step_name} ({self.duration_minutes}min, touch={self.is_touch})>"
