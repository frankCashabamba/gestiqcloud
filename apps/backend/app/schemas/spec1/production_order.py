"""
Production Order Schemas - Pydantic models for SPEC-1 production orders
"""
from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from datetime import date, datetime
from typing import Optional, List
from decimal import Decimal


class ProductionOrderLineBase(BaseModel):
    """Base schema for production order line (component)"""
    product_id: UUID
    qty_required: Decimal = Field(..., gt=0, decimal_places=3)
    qty_consumed: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=3)

    @field_validator("qty_required")
    @classmethod
    def validate_qty_positive(cls, v):
        """Ensure qty_required is positive"""
        if v <= 0:
            raise ValueError("Cantidad requerida debe ser mayor que cero")
        return v


class ProductionOrderBase(BaseModel):
    """Base schema for production order"""
    fecha: date
    product_id: UUID  # Product to produce
    qty_to_produce: Decimal = Field(..., gt=0, decimal_places=3)
    qty_produced: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=3)
    status: str = Field(default="draft", pattern="^(draft|in_progress|completed|cancelled)$")
    warehouse_id: Optional[UUID] = None
    notas: Optional[str] = Field(None, max_length=1000)

    @field_validator("qty_to_produce")
    @classmethod
    def validate_qty_to_produce_positive(cls, v):
        """Ensure qty_to_produce is positive"""
        if v <= 0:
            raise ValueError("Cantidad a producir debe ser mayor que cero")
        return v


class ProductionOrderCreate(ProductionOrderBase):
    """Create production order"""
    components: List[ProductionOrderLineBase] = Field(default_factory=list)


class ProductionOrderUpdate(BaseModel):
    """Update production order"""
    fecha: Optional[date] = None
    qty_to_produce: Optional[Decimal] = Field(None, gt=0, decimal_places=3)
    qty_produced: Optional[Decimal] = Field(None, ge=0, decimal_places=3)
    status: Optional[str] = Field(None, pattern="^(draft|in_progress|completed|cancelled)$")
    notas: Optional[str] = Field(None, max_length=1000)


class ProductionOrderLineResponse(BaseModel):
    """Production order line response"""
    id: UUID
    production_order_id: UUID
    product_id: UUID
    qty_required: Decimal
    qty_consumed: Decimal

    class Config:
        from_attributes = True


class ProductionOrderResponse(BaseModel):
    """Production order response"""
    id: UUID
    tenant_id: UUID
    fecha: date
    product_id: UUID
    qty_to_produce: Decimal
    qty_produced: Decimal
    status: str
    warehouse_id: Optional[UUID] = None
    notas: Optional[str] = None
    created_at: datetime
    created_by: Optional[UUID] = None
    components: List[ProductionOrderLineResponse] = []

    class Config:
        from_attributes = True


class ProductionOrderSummary(BaseModel):
    """Production order summary"""
    start_date: date
    end_date: date
    total_orders: int
    total_qty_produced: Decimal
    orders_by_status: dict[str, int]
