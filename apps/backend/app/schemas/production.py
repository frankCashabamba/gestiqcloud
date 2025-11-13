"""
Production Schemas - Esquemas Pydantic para órdenes de producción
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, validator

# ============================================================================
# LÍNEAS DE ORDEN
# ============================================================================


class ProductionOrderLineBase(BaseModel):
    """Base para líneas de orden de producción"""

    ingredient_product_id: UUID = Field(..., description="ID del producto ingrediente")
    qty_required: Decimal = Field(..., gt=0, description="Cantidad requerida")
    qty_consumed: Decimal = Field(default=Decimal("0"), ge=0, description="Cantidad consumida")
    unit: str = Field(default="unit", description="Unidad de medida")
    cost_unit: Decimal = Field(default=Decimal("0"), ge=0, description="Costo unitario")


class ProductionOrderLineCreate(ProductionOrderLineBase):
    """Schema para crear línea de orden"""

    pass


class ProductionOrderLineResponse(ProductionOrderLineBase):
    """Schema de respuesta para línea"""

    id: UUID
    order_id: UUID
    stock_move_id: UUID | None
    cost_total: Decimal
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# ÓRDENES DE PRODUCCIÓN
# ============================================================================


class ProductionOrderBase(BaseModel):
    """Base para órdenes de producción"""

    recipe_id: UUID = Field(..., description="ID de la receta")
    product_id: UUID = Field(..., description="ID del producto a producir")
    warehouse_id: UUID | None = Field(None, description="ID del almacén")
    qty_planned: Decimal = Field(..., gt=0, description="Cantidad planificada")
    scheduled_date: datetime | None = Field(None, description="Fecha programada")
    notes: str | None = Field(None, description="Notas internas")


class ProductionOrderCreate(ProductionOrderBase):
    """Schema para crear orden de producción"""

    lines: list[ProductionOrderLineCreate] | None = Field(
        default_factory=list,
        description="Líneas de ingredientes (opcional, se auto-genera desde receta)",
    )

    @validator("qty_planned")
    def validate_qty_planned(cls, v):
        if v <= 0:
            raise ValueError("La cantidad planificada debe ser mayor a 0")
        return v


class ProductionOrderUpdate(BaseModel):
    """Schema para actualizar orden de producción"""

    qty_produced: Decimal | None = Field(None, ge=0)
    waste_qty: Decimal | None = Field(None, ge=0)
    waste_reason: str | None = None
    scheduled_date: datetime | None = None
    notes: str | None = None
    status: str | None = Field(None, pattern="^(DRAFT|SCHEDULED|IN_PROGRESS|COMPLETED|CANCELLED)$")


class ProductionOrderStartRequest(BaseModel):
    """Schema para iniciar producción"""

    started_at: datetime | None = Field(
        default_factory=datetime.utcnow, description="Fecha/hora de inicio"
    )
    notes: str | None = Field(None, description="Notas de inicio")


class ProductionOrderCompleteRequest(BaseModel):
    """Schema para completar producción"""

    qty_produced: Decimal = Field(..., gt=0, description="Cantidad producida")
    waste_qty: Decimal = Field(default=Decimal("0"), ge=0, description="Mermas")
    waste_reason: str | None = Field(None, description="Motivo de mermas")
    batch_number: str | None = Field(None, description="Número de lote")
    completed_at: datetime | None = Field(
        default_factory=datetime.utcnow, description="Fecha/hora de finalización"
    )
    notes: str | None = Field(None, description="Notas de cierre")

    @validator("qty_produced")
    def validate_qty_produced(cls, v):
        if v <= 0:
            raise ValueError("La cantidad producida debe ser mayor a 0")
        return v


class ProductionOrderResponse(ProductionOrderBase):
    """Schema de respuesta completo"""

    id: UUID
    tenant_id: UUID
    numero: str
    qty_produced: Decimal
    waste_qty: Decimal
    waste_reason: str | None
    started_at: datetime | None
    completed_at: datetime | None
    status: str
    batch_number: str | None
    metadata_json: dict | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

    # Relaciones
    lines: list[ProductionOrderLineResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ProductionOrderList(BaseModel):
    """Schema para lista paginada"""

    items: list[ProductionOrderResponse]
    total: int
    skip: int
    limit: int


class ProductionOrderStats(BaseModel):
    """Estadísticas de producción"""

    total_orders: int = Field(default=0, description="Total de órdenes")
    completed: int = Field(default=0, description="Completadas")
    in_progress: int = Field(default=0, description="En proceso")
    scheduled: int = Field(default=0, description="Programadas")
    cancelled: int = Field(default=0, description="Canceladas")
    total_qty_produced: Decimal = Field(
        default=Decimal("0"), description="Cantidad total producida"
    )
    total_waste_qty: Decimal = Field(default=Decimal("0"), description="Mermas totales")
    waste_percentage: float = Field(default=0.0, description="Porcentaje de mermas")
    avg_production_time_hours: float = Field(default=0.0, description="Tiempo promedio (horas)")


# ============================================================================
# CALCULADORA DE PRODUCCIÓN (para planificación)
# ============================================================================


class ProductionCalculatorRequest(BaseModel):
    """Request para calcular necesidades de producción"""

    recipe_id: UUID = Field(..., description="ID de la receta")
    qty_desired: Decimal = Field(..., gt=0, description="Cantidad deseada a producir")


class IngredientRequirement(BaseModel):
    """Ingrediente requerido"""

    ingredient_id: UUID
    ingredient_name: str
    qty_required: Decimal
    unit: str
    stock_available: Decimal
    stock_sufficient: bool
    qty_to_purchase: Decimal


class ProductionCalculatorResponse(BaseModel):
    """Respuesta de calculadora de producción"""

    recipe_id: UUID
    recipe_name: str
    qty_desired: Decimal
    qty_producible: Decimal
    can_produce: bool
    missing_ingredients: list[IngredientRequirement]
    all_ingredients: list[IngredientRequirement]
    estimated_cost: Decimal
    production_time_minutes: int | None
