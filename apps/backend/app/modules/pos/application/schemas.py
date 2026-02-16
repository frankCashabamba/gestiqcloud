"""POS Module: Pydantic schemas para request/response."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class PaymentMethodModel(BaseModel):
    """Método de pago en recibo."""

    method: Literal["cash", "card", "check", "transfer", "mixed"]
    amount: Decimal = Field(gt=0, decimal_places=2)
    ref: str | None = Field(None, max_length=200)


class ReceiptLineModel(BaseModel):
    """Línea de producto en recibo."""

    product_id: UUID
    product_name: str = Field(max_length=255)
    qty: Decimal = Field(gt=0, decimal_places=3)
    unit_price: Decimal = Field(ge=0, decimal_places=4)
    tax_rate: Decimal = Field(ge=0, le=1, decimal_places=4, default=Decimal("0"))
    discount_pct: Decimal = Field(ge=0, le=100, decimal_places=2, default=Decimal("0"))
    uom: str = Field(default="unit", max_length=20)

    @property
    def line_subtotal(self) -> Decimal:
        """Subtotal sin impuesto."""
        subtotal = self.qty * self.unit_price
        discount = subtotal * (self.discount_pct / 100)
        return subtotal - discount

    @property
    def line_tax(self) -> Decimal:
        """Impuesto de la línea."""
        return self.line_subtotal * self.tax_rate

    @property
    def line_total(self) -> Decimal:
        """Total con impuesto."""
        return self.line_subtotal + self.line_tax


# ============================================================================
# REQUEST MODELS
# ============================================================================


class OpenShiftRequest(BaseModel):
    """Request: abrir turno."""

    register_id: UUID
    opening_float: Decimal = Field(ge=0, decimal_places=2, default=Decimal("0"))


class CreateReceiptRequest(BaseModel):
    """Request: crear recibo."""

    shift_id: UUID
    register_id: UUID
    customer_id: UUID | None = None
    lines: list[ReceiptLineModel] = Field(min_length=1)
    notes: str | None = Field(None, max_length=500)


class CheckoutRequest(BaseModel):
    """Request: pagar recibo."""

    payments: list[PaymentMethodModel] = Field(min_length=1)
    warehouse_id: UUID | None = None
    notes: str | None = Field(None, max_length=500)


class CloseShiftRequest(BaseModel):
    """Request: cerrar turno."""

    cash_count: Decimal = Field(ge=0, decimal_places=2)
    notes: str | None = Field(None, max_length=500)


class UpdateNumberingCounterRequest(BaseModel):
    """Request: actualizar contador de numeración."""

    doc_type: str = Field(max_length=30)
    series: str = Field(default="A", max_length=50)
    year: int = Field(ge=2000)
    current_no: int = Field(ge=0)


# ============================================================================
# RESPONSE MODELS
# ============================================================================


class ShiftResponse(BaseModel):
    """Response: turno."""

    id: UUID
    register_id: UUID
    cashier_id: UUID
    status: Literal["open", "closed"]
    opening_float: Decimal
    opened_at: datetime
    closed_at: datetime | None = None

    class Config:
        from_attributes = True


class ReceiptResponse(BaseModel):
    """Response: recibo completo."""

    id: UUID
    shift_id: UUID
    register_id: UUID
    customer_id: UUID | None = None
    number: str
    status: Literal["draft", "paid", "voided"]
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    lines: list[ReceiptLineModel]
    payments: list[PaymentMethodModel] = Field(default_factory=list)
    created_at: datetime
    paid_at: datetime | None = None
    notes: str | None = None

    class Config:
        from_attributes = True


class ReceiptSummaryResponse(BaseModel):
    """Response: resumen de recibo (minimal)."""

    id: UUID
    number: str
    total: Decimal
    status: str
    created_at: datetime


class ShiftSummaryResponse(BaseModel):
    """Response: resumen de cierre de turno."""

    shift_id: UUID
    register_id: UUID
    opened_at: datetime
    closed_at: datetime
    opening_float: Decimal
    cash_count: Decimal
    receipts_count: int
    sales_total: Decimal
    expected_cash: Decimal
    variance: Decimal
    variance_pct: Decimal


class NumberingCounterResponse(BaseModel):
    """Response: contador de numeración."""

    doc_type: str
    series: str
    year: int
    current_no: int
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    """Response: health check."""

    status: Literal["ok", "degraded"]
    timestamp: datetime
    version: str = "1.0"
