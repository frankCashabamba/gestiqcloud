"""Invoicing module Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class InvoiceLineModel(BaseModel):
    """Invoice line."""

    description: str = Field(max_length=500)
    qty: Decimal = Field(gt=0, decimal_places=3)
    unit_price: Decimal = Field(ge=0, decimal_places=4)
    tax_rate: Decimal = Field(ge=0, le=1, decimal_places=4, default=Decimal("0"))
    amount: Decimal = Field(decimal_places=2)


class CustomerModel(BaseModel):
    """Invoice customer data."""

    id: UUID
    name: str = Field(max_length=255)
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    tax_id: str | None = None  # RUT, RFC, etc


# ============================================================================
# REQUESTS
# ============================================================================


class CreateInvoiceRequest(BaseModel):
    """Request: create invoice."""

    customer_id: UUID | None = None
    lines: list[InvoiceLineModel] = Field(min_length=1)
    notes: str | None = Field(None, max_length=500)
    due_days: int = Field(default=30, ge=0, le=365)


class CreateInvoiceFromReceiptRequest(BaseModel):
    """Request: create invoice from a POS receipt."""

    receipt_id: UUID
    customer_id: UUID | None = None


class SendInvoiceEmailRequest(BaseModel):
    """Request: send invoice by email."""

    recipient_email: str = Field(max_length=255)
    template: Literal["default", "es", "en"] = "default"
    include_attachment: bool = True


class MarkInvoiceAsPaidRequest(BaseModel):
    """Request: mark invoice as paid."""

    paid_amount: Decimal = Field(gt=0, decimal_places=2)
    payment_method: Literal["cash", "card", "transfer", "check"]
    payment_ref: str | None = Field(None, max_length=200)


# ============================================================================
# RESPONSES
# ============================================================================


class InvoiceResponse(BaseModel):
    """Response: full invoice."""

    id: UUID
    number: str
    status: Literal["draft", "sent", "paid", "voided"]
    customer: CustomerModel | None = None
    lines: list[InvoiceLineModel]
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    notes: str | None = None
    issued_at: datetime
    due_date: datetime
    sent_at: datetime | None = None
    paid_at: datetime | None = None

    class Config:
        from_attributes = True


class InvoiceSummaryResponse(BaseModel):
    """Response: invoice summary."""

    id: UUID
    number: str
    status: str
    total: Decimal
    issued_at: datetime
    due_date: datetime
    customer_name: str | None = None


class InvoiceListResponse(BaseModel):
    """Response: invoice list."""

    invoices: list[InvoiceSummaryResponse]
    total_count: int
    page: int = 1
    page_size: int = 20
    total_pages: int


class SendEmailResponse(BaseModel):
    """Response: email delivery."""

    invoice_id: UUID
    sent_at: datetime
    recipient: str
    status: Literal["sent", "failed"]


class PaymentRecordResponse(BaseModel):
    """Response: payment record."""

    id: UUID
    invoice_id: UUID
    amount: Decimal
    method: str
    ref: str | None = None
    recorded_at: datetime

    class Config:
        from_attributes = True
