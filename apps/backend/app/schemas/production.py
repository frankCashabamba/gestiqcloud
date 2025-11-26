"""
Production Schemas - Pydantic models for production orders
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ============================================================================
# ORDER LINES
# ============================================================================


class ProductionOrderLineBase(BaseModel):
    """Base for production order lines."""

    ingredient_product_id: UUID = Field(..., description="Ingredient product ID")
    qty_required: Decimal = Field(..., gt=0, description="Required quantity")
    qty_consumed: Decimal = Field(default=Decimal("0"), ge=0, description="Consumed quantity")
    unit: str = Field(default="unit", description="Unit of measure")
    cost_unit: Decimal = Field(default=Decimal("0"), ge=0, description="Unit cost")


class ProductionOrderLineCreate(ProductionOrderLineBase):
    """Create production order line."""


class ProductionOrderLineResponse(ProductionOrderLineBase):
    """Production order line response."""

    id: UUID
    order_id: UUID
    stock_move_id: UUID | None
    cost_total: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# PRODUCTION ORDERS
# ============================================================================


class ProductionOrderBase(BaseModel):
    """Base for production orders."""

    recipe_id: UUID = Field(..., description="Recipe ID")
    product_id: UUID = Field(..., description="Product to produce")
    warehouse_id: UUID | None = Field(None, description="Warehouse ID")
    qty_planned: Decimal = Field(..., gt=0, description="Planned quantity")
    scheduled_date: datetime | None = Field(None, description="Scheduled date")
    notes: str | None = Field(None, description="Internal notes")


class ProductionOrderCreate(ProductionOrderBase):
    """Create production order."""

    lines: list[ProductionOrderLineCreate] | None = Field(
        default_factory=list,
        description="Ingredient lines (optional, auto-generated from recipe)",
    )

    @field_validator("qty_planned")
    @classmethod
    def validate_qty_planned(cls, v):
        if v <= 0:
            raise ValueError("Planned quantity must be greater than 0")
        return v


class ProductionOrderUpdate(BaseModel):
    """Update production order."""

    qty_produced: Decimal | None = Field(None, ge=0)
    waste_qty: Decimal | None = Field(None, ge=0)
    waste_reason: str | None = None
    scheduled_date: datetime | None = None
    notes: str | None = None
    status: str | None = Field(None, pattern="^(DRAFT|SCHEDULED|IN_PROGRESS|COMPLETED|CANCELLED)$")


class ProductionOrderStartRequest(BaseModel):
    """Start production."""

    started_at: datetime | None = Field(
        default_factory=datetime.utcnow, description="Start datetime"
    )
    notes: str | None = Field(None, description="Start notes")


class ProductionOrderCompleteRequest(BaseModel):
    """Complete production."""

    qty_produced: Decimal = Field(..., gt=0, description="Produced quantity")
    waste_qty: Decimal = Field(default=Decimal("0"), ge=0, description="Waste")
    waste_reason: str | None = Field(None, description="Waste reason")
    batch_number: str | None = Field(None, description="Batch number")
    completed_at: datetime | None = Field(
        default_factory=datetime.utcnow, description="Completion datetime"
    )
    notes: str | None = Field(None, description="Closing notes")

    @field_validator("qty_produced")
    @classmethod
    def validate_qty_produced(cls, v):
        if v <= 0:
            raise ValueError("Produced quantity must be greater than 0")
        return v


class ProductionOrderResponse(ProductionOrderBase):
    """Full production order response."""

    id: UUID
    tenant_id: UUID
    order_number: str = Field(alias="numero")
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

    # Relationships
    lines: list[ProductionOrderLineResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


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
    """Request to calculate production needs."""

    recipe_id: UUID = Field(..., description="Recipe ID")
    qty_desired: Decimal = Field(..., gt=0, description="Desired quantity to produce")


class IngredientRequirement(BaseModel):
    """Required ingredient."""

    ingredient_id: UUID
    ingredient_name: str
    qty_required: Decimal
    unit: str
    stock_available: Decimal
    stock_sufficient: bool
    qty_to_purchase: Decimal


class ProductionCalculatorResponse(BaseModel):
    """Production calculator response."""

    recipe_id: UUID
    recipe_name: str
    qty_desired: Decimal
    qty_producible: Decimal
    can_produce: bool
    missing_ingredients: list[IngredientRequirement]
    all_ingredients: list[IngredientRequirement]
    estimated_cost: Decimal
    production_time_minutes: int | None
