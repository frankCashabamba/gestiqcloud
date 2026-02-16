"""SALES Module: Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SalesOrderLineModel(BaseModel):
    """Sales order line."""

    product_id: UUID
    product_name: str = Field(max_length=255)
    qty: Decimal = Field(gt=0, decimal_places=3)
    unit_price: Decimal = Field(ge=0, decimal_places=4)
    discount_pct: Decimal = Field(ge=0, le=100, decimal_places=2, default=Decimal("0"))

    @property
    def line_subtotal(self) -> Decimal:
        """Subtotal without discount."""
        return self.qty * self.unit_price * (1 - self.discount_pct / 100)

    @property
    def line_total(self) -> Decimal:
        """Total with tax."""
        return self.line_subtotal * Decimal("1.21")  # IVA 21%


class CustomerModel(BaseModel):
    """Customer info in sales order."""

    id: UUID
    name: str = Field(max_length=255)
    email: str | None = None
    tax_id: str | None = None

    class Config:
        from_attributes = True


# ============================================================================
# REQUESTS
# ============================================================================


class CreateSalesOrderRequest(BaseModel):
    """Request: create sales order."""

    customer_id: UUID
    lines: list[SalesOrderLineModel] = Field(min_length=1)
    notes: str | None = Field(None, max_length=500)


class ApproveSalesOrderRequest(BaseModel):
    """Request: approve sales order."""

    pass  # Approval is implicit from user context


class CancelSalesOrderRequest(BaseModel):
    """Request: cancel sales order."""

    reason: str = Field(max_length=500)


class CreateInvoiceFromOrderRequest(BaseModel):
    """Request: create invoice from order."""

    pass  # Invoice creation is implicit from order


# ============================================================================
# RESPONSES
# ============================================================================


class SalesOrderResponse(BaseModel):
    """Response: sales order complete."""

    id: UUID
    number: str
    status: Literal["draft", "approved", "invoiced", "shipped", "paid", "cancelled"]
    customer: CustomerModel
    lines: list[SalesOrderLineModel]
    subtotal: Decimal
    discount: Decimal
    tax: Decimal
    total: Decimal
    notes: str | None = None
    created_at: datetime
    approved_at: datetime | None = None
    invoice_id: UUID | None = None
    shipped_at: datetime | None = None
    paid_at: datetime | None = None

    class Config:
        from_attributes = True


class SalesOrderSummaryResponse(BaseModel):
    """Response: sales order summary."""

    id: UUID
    number: str
    status: str
    customer_name: str
    total: Decimal
    created_at: datetime
    approved_at: datetime | None = None


class SalesOrderListResponse(BaseModel):
    """Response: list of sales orders."""

    orders: list[SalesOrderSummaryResponse]
    total_count: int
    page: int = 1
    page_size: int = 20
    total_pages: int


class SalesOrderApprovalResponse(BaseModel):
    """Response: order approval."""

    order_id: UUID
    status: str = "approved"
    approved_at: datetime
    approved_by: UUID


class SalesOrderCancellationResponse(BaseModel):
    """Response: order cancellation."""

    order_id: UUID
    status: str = "cancelled"
    cancelled_at: datetime
    cancelled_by: UUID
    reason: str
