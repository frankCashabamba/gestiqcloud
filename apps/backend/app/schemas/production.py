"""Production schemas."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

ProductionOrderStatus = Literal["DRAFT", "SCHEDULED", "IN_PROGRESS", "COMPLETED", "CANCELLED"]


class ProductionOrderLineBase(BaseModel):
    ingredient_product_id: UUID = Field(..., description="Ingredient product ID")
    quantity_required: Decimal = Field(..., gt=0)
    quantity_consumed: Decimal = Field(default=Decimal("0"), ge=0)
    unit: str = Field(default="unit")
    unit_cost: Decimal = Field(default=Decimal("0"), ge=0)

    @property
    def qty_required(self) -> Decimal:
        return self.quantity_required

    @qty_required.setter
    def qty_required(self, value: Decimal) -> None:
        self.quantity_required = value

    @property
    def qty_consumed(self) -> Decimal:
        return self.quantity_consumed

    @qty_consumed.setter
    def qty_consumed(self, value: Decimal) -> None:
        self.quantity_consumed = value

    @property
    def cost_unit(self) -> Decimal:
        return self.unit_cost

    @cost_unit.setter
    def cost_unit(self, value: Decimal) -> None:
        self.unit_cost = value


class ProductionOrderLineCreate(ProductionOrderLineBase):
    pass


class ProductionOrderLineResponse(ProductionOrderLineBase):
    id: UUID
    order_id: UUID
    stock_move_id: UUID | None
    cost_total: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductionOrderBase(BaseModel):
    recipe_id: UUID
    product_id: UUID
    warehouse_id: UUID | None = None
    quantity_planned: Decimal = Field(..., gt=0)
    scheduled_date: datetime | None = None
    notes: str | None = None

    @property
    def qty_planned(self) -> Decimal:
        return self.quantity_planned

    @qty_planned.setter
    def qty_planned(self, value: Decimal) -> None:
        self.quantity_planned = value


class ProductionOrderCreate(ProductionOrderBase):
    lines: list[ProductionOrderLineCreate] | None = Field(default_factory=list)

    @field_validator("quantity_planned")
    @classmethod
    def validate_quantity_planned(cls, value):
        if value <= 0:
            raise ValueError("Planned quantity must be greater than 0")
        return value


class ProductionOrderUpdate(BaseModel):
    quantity_produced: Decimal | None = Field(None, ge=0)
    waste_quantity: Decimal | None = Field(None, ge=0)
    waste_reason: str | None = None
    scheduled_date: datetime | None = None
    notes: str | None = None
    status: ProductionOrderStatus | None = None

    @property
    def qty_produced(self) -> Decimal | None:
        return self.quantity_produced

    @property
    def waste_qty(self) -> Decimal | None:
        return self.waste_quantity


class ProductionOrderStartRequest(BaseModel):
    started_at: datetime | None = Field(
        default_factory=lambda: datetime.now(UTC),
    )
    notes: str | None = None


class ProductionOrderCompleteRequest(BaseModel):
    quantity_produced: Decimal = Field(..., gt=0)
    waste_quantity: Decimal = Field(default=Decimal("0"), ge=0)
    waste_reason: str | None = None
    batch_number: str | None = None
    completed_at: datetime | None = Field(default_factory=lambda: datetime.now(UTC))
    notes: str | None = None

    @property
    def qty_produced(self) -> Decimal:
        return self.quantity_produced

    @property
    def waste_qty(self) -> Decimal:
        return self.waste_quantity

    @field_validator("quantity_produced")
    @classmethod
    def validate_quantity_produced(cls, value):
        if value <= 0:
            raise ValueError("Produced quantity must be greater than 0")
        return value


class ProductionOrderResponse(ProductionOrderBase):
    id: UUID
    tenant_id: UUID
    order_number: str
    quantity_produced: Decimal
    waste_quantity: Decimal
    waste_reason: str | None
    started_at: datetime | None
    completed_at: datetime | None
    status: ProductionOrderStatus
    batch_number: str | None
    metadata_json: dict | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime
    lines: list[ProductionOrderLineResponse] = Field(default_factory=list)

    @property
    def numero(self) -> str:
        return self.order_number

    model_config = ConfigDict(from_attributes=True)


class ProductionOrderList(BaseModel):
    items: list[ProductionOrderResponse]
    total: int
    skip: int
    limit: int


class ProductionOrderStats(BaseModel):
    total_orders: int = Field(default=0)
    completed: int = Field(default=0)
    in_progress: int = Field(default=0)
    scheduled: int = Field(default=0)
    cancelled: int = Field(default=0)
    total_quantity_produced: Decimal = Field(default=Decimal("0"))
    total_waste_quantity: Decimal = Field(default=Decimal("0"))
    waste_percentage: float = Field(default=0.0)
    avg_production_time_hours: float = Field(default=0.0)


class ProductionCalculatorRequest(BaseModel):
    recipe_id: UUID
    quantity_desired: Decimal = Field(..., gt=0)

    @property
    def qty_desired(self) -> Decimal:
        return self.quantity_desired


class IngredientRequirement(BaseModel):
    ingredient_id: UUID
    ingredient_name: str
    quantity_required: Decimal
    unit: str
    stock_available: Decimal
    stock_sufficient: bool
    quantity_to_purchase: Decimal

    @property
    def qty_required(self) -> Decimal:
        return self.quantity_required

    @property
    def qty_to_purchase(self) -> Decimal:
        return self.quantity_to_purchase


class ProductionCalculatorResponse(BaseModel):
    recipe_id: UUID
    recipe_name: str
    quantity_desired: Decimal
    quantity_producible: Decimal
    can_produce: bool
    missing_ingredients: list[IngredientRequirement]
    all_ingredients: list[IngredientRequirement]
    estimated_cost: Decimal
    production_time_minutes: int | None

    @property
    def qty_desired(self) -> Decimal:
        return self.quantity_desired

    @property
    def qty_producible(self) -> Decimal:
        return self.quantity_producible


class ProductionPlanningSuggestion(BaseModel):
    recipe_id: UUID
    product_id: UUID
    recipe_name: str
    product_name: str
    target_date: str
    average_daily_sales: Decimal
    stock_on_hand: Decimal
    already_planned_quantity: Decimal
    suggested_quantity: Decimal

    @property
    def avg_daily_sales(self) -> Decimal:
        return self.average_daily_sales

    @property
    def already_planned_qty(self) -> Decimal:
        return self.already_planned_quantity

    @property
    def suggested_qty(self) -> Decimal:
        return self.suggested_quantity
