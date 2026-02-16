"""INVENTORY Module: Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class WarehouseModel(BaseModel):
    """Warehouse info."""

    id: UUID
    name: str = Field(max_length=255)
    code: str = Field(max_length=50)
    location: str | None = None
    is_default: bool = False
    is_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


class StockItemModel(BaseModel):
    """Stock item in warehouse."""

    id: UUID
    product_id: UUID
    warehouse_id: UUID
    qty: Decimal = Field(decimal_places=3)
    unit_cost: Decimal = Field(decimal_places=4)
    total_cost: Decimal = Field(decimal_places=2)
    min_qty: Decimal = Field(default=Decimal("0"), decimal_places=3)
    last_movement: datetime | None = None

    class Config:
        from_attributes = True


class StockMoveModel(BaseModel):
    """Stock movement record."""

    id: UUID
    product_id: UUID
    warehouse_id: UUID
    move_type: str  # purchase, sale, adjustment, transfer
    qty: Decimal = Field(decimal_places=3)
    unit_cost: Decimal | None = Field(None, decimal_places=4)
    reference_id: UUID | None = None
    notes: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# REQUESTS
# ============================================================================


class CreateWarehouseRequest(BaseModel):
    """Request: create warehouse."""

    name: str = Field(max_length=255)
    code: str = Field(max_length=50)
    location: str | None = None
    is_default: bool = False


class ReceiveStockRequest(BaseModel):
    """Request: receive stock from purchase."""

    warehouse_id: UUID
    lines: list[dict] = Field(
        min_length=1,
        description="List of {product_id, qty, unit_cost}",
    )
    po_id: UUID | None = None


class AdjustStockRequest(BaseModel):
    """Request: adjust stock manually."""

    warehouse_id: UUID
    product_id: UUID
    qty_adjustment: Decimal = Field(
        decimal_places=3,
        description="Positive = increase, Negative = decrease",
    )
    reason: str = Field(max_length=500)


class TransferStockRequest(BaseModel):
    """Request: transfer stock between warehouses."""

    from_warehouse_id: UUID
    to_warehouse_id: UUID
    product_id: UUID
    qty: Decimal = Field(gt=0, decimal_places=3)


# ============================================================================
# RESPONSES
# ============================================================================


class WarehouseResponse(BaseModel):
    """Response: warehouse info."""

    id: UUID
    name: str
    code: str
    location: str | None = None
    is_default: bool
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class StockReceiptResponse(BaseModel):
    """Response: stock receipt."""

    receipt_id: UUID
    warehouse_id: UUID
    po_id: UUID | None = None
    lines_received: int
    total_cost: Decimal
    created_at: datetime


class StockAdjustmentResponse(BaseModel):
    """Response: stock adjustment."""

    move_id: UUID
    warehouse_id: UUID
    product_id: UUID
    qty_adjustment: Decimal
    new_qty: Decimal
    reason: str
    created_at: datetime


class StockTransferResponse(BaseModel):
    """Response: stock transfer."""

    transfer_id: UUID
    from_warehouse_id: UUID
    to_warehouse_id: UUID
    product_id: UUID
    qty: Decimal
    status: str
    created_at: datetime


class InventorySummaryResponse(BaseModel):
    """Response: inventory summary."""

    warehouse_id: UUID | None
    costing_method: str
    total_value: Decimal
    items_count: int
    calculated_at: datetime


class LowStockAlertResponse(BaseModel):
    """Response: low stock alert."""

    product_id: UUID
    product_name: str
    current_qty: Decimal
    min_qty: Decimal
    warehouse: str
    alert_level: str  # critical, warning


class StockAlertsResponse(BaseModel):
    """Response: list of stock alerts."""

    alerts: list[LowStockAlertResponse]
    total_alerts: int
