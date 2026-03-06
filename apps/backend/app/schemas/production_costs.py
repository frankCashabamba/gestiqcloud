"""
Production Cost Schemas - Pydantic models for cost drivers, recipe cost lines, and order costs
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# COST DRIVERS (catalog)
# ============================================================================


class CostDriverBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=30, description="Unique code per tenant")
    name: str = Field(..., min_length=1, max_length=100, description="Display name")
    unit: str = Field(default="hour", max_length=20, description="hour, kwh, unit, flat")
    default_rate: Decimal = Field(default=Decimal("0"), ge=0, description="Default cost per unit")
    consumption_rate: Decimal | None = Field(None, ge=0, description="Auto-calc consumption (L/hr, kWh/hr, etc.)")
    is_active: bool = Field(default=True)


class CostDriverCreate(CostDriverBase):
    model_config = ConfigDict(extra="forbid")


class CostDriverUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str | None = Field(None, min_length=1, max_length=30)
    name: str | None = Field(None, min_length=1, max_length=100)
    unit: str | None = Field(None, max_length=20)
    default_rate: Decimal | None = Field(None, ge=0)
    consumption_rate: Decimal | None = Field(None, ge=0)
    is_active: bool | None = None


class CostDriverResponse(CostDriverBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# RECIPE COST LINES (standard costs per recipe)
# ============================================================================


class RecipeCostLineBase(BaseModel):
    driver_id: UUID = Field(..., description="Cost driver ID")
    qty_standard: Decimal = Field(default=Decimal("0"), ge=0, description="Standard quantity")
    headcount: int = Field(default=1, ge=1, description="Number of people (for labor)")
    rate_override: Decimal | None = Field(
        None, ge=0, description="Override rate (null = use driver default)"
    )
    notes: str | None = None
    line_order: int = Field(default=0, ge=0)


class RecipeCostLineCreate(RecipeCostLineBase):
    model_config = ConfigDict(extra="forbid")


class RecipeCostLineUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    driver_id: UUID | None = None
    qty_standard: Decimal | None = Field(None, ge=0)
    headcount: int | None = Field(None, ge=1)
    rate_override: Decimal | None = Field(None, ge=0)
    notes: str | None = None
    line_order: int | None = Field(None, ge=0)


class RecipeCostLineResponse(RecipeCostLineBase):
    id: UUID
    recipe_id: UUID
    created_at: datetime

    # Joined driver info
    driver_code: str | None = None
    driver_name: str | None = None
    driver_unit: str | None = None
    driver_default_rate: Decimal | None = None
    driver_consumption_rate: Decimal | None = None

    # Calculated
    effective_rate: Decimal | None = None
    line_cost: Decimal | None = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# PRODUCTION ORDER COSTS (actual costs per batch)
# ============================================================================


class OrderCostBase(BaseModel):
    driver_id: UUID = Field(..., description="Cost driver ID")
    qty_actual: Decimal = Field(default=Decimal("0"), ge=0, description="Actual quantity")
    headcount_actual: int = Field(default=1, ge=1, description="Actual headcount")
    rate_applied: Decimal = Field(default=Decimal("0"), ge=0, description="Rate applied")
    notes: str | None = None


class OrderCostCreate(OrderCostBase):
    model_config = ConfigDict(extra="forbid")


class OrderCostUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    driver_id: UUID | None = None
    qty_actual: Decimal | None = Field(None, ge=0)
    headcount_actual: int | None = Field(None, ge=1)
    rate_applied: Decimal | None = Field(None, ge=0)
    notes: str | None = None


class OrderCostResponse(OrderCostBase):
    id: UUID
    order_id: UUID
    cost_total: Decimal
    created_at: datetime

    # Joined driver info
    driver_code: str | None = None
    driver_name: str | None = None
    driver_unit: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# FULL COST SUMMARY (for UI cards)
# ============================================================================


class RecipeFullCostSummary(BaseModel):
    """Full cost breakdown for a recipe - materials + indirect costs."""

    recipe_id: str
    recipe_name: str
    yield_qty: int

    # Materials (ingredients)
    materials_total: Decimal = Field(default=Decimal("0"))
    materials_unit: Decimal = Field(default=Decimal("0"))

    # Indirect costs (from cost lines)
    labor_total: Decimal = Field(default=Decimal("0"))
    energy_total: Decimal = Field(default=Decimal("0"))
    other_indirect_total: Decimal = Field(default=Decimal("0"))
    indirect_total: Decimal = Field(default=Decimal("0"))

    # Full cost
    full_cost_total: Decimal = Field(default=Decimal("0"))
    full_cost_unit: Decimal = Field(default=Decimal("0"))

    # Cost lines detail
    cost_lines: list[RecipeCostLineResponse] = Field(default_factory=list)
