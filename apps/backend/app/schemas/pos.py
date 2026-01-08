"""Schemas Pydantic para POS"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ==================== REGISTER SCHEMAS ====================
class POSRegisterBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    store_id: UUID | None = None
    active: bool = True


class POSRegisterCreate(POSRegisterBase):
    pass


class POSRegisterUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    active: bool | None = None


class POSRegisterResponse(POSRegisterBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_at: datetime


# ==================== SHIFT SCHEMAS ====================
class POSShiftBase(BaseModel):
    opening_float: Decimal = Field(..., ge=0, decimal_places=2)


class POSShiftCreate(POSShiftBase):
    register_id: UUID


class POSShiftClose(BaseModel):
    closing_total: Decimal = Field(..., ge=0, decimal_places=2)


class POSShiftResponse(POSShiftBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    register_id: UUID
    opened_by: UUID
    opened_at: datetime
    closed_at: datetime | None = None
    closing_total: Decimal | None = None
    status: str


# ==================== RECEIPT LINE SCHEMAS ====================
class POSReceiptLineBase(BaseModel):
    product_id: UUID
    qty: Decimal = Field(..., gt=0, decimal_places=3)
    uom: str = Field(default="unit", max_length=20)
    unit_price: Decimal = Field(..., ge=0, decimal_places=4)
    tax_rate: Decimal = Field(..., ge=0, le=1, decimal_places=4)
    discount_pct: Decimal = Field(default=Decimal("0"), ge=0, le=100, decimal_places=2)


class POSReceiptLineCreate(POSReceiptLineBase):
    pass


class POSReceiptLineResponse(POSReceiptLineBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    receipt_id: UUID
    line_total: Decimal


# ==================== PAYMENT SCHEMAS ====================
class POSPaymentBase(BaseModel):
    method: str = Field(..., pattern="^(cash|card|store_credit|link)$")
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    ref: str | None = None


class POSPaymentCreate(POSPaymentBase):
    pass


class POSPaymentResponse(POSPaymentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    receipt_id: UUID
    paid_at: datetime


# ==================== RECEIPT SCHEMAS ====================
class POSReceiptBase(BaseModel):
    customer_id: UUID | None = None
    currency: str = Field(default="EUR", pattern="^(EUR|USD)$")


class POSReceiptCreate(POSReceiptBase):
    register_id: UUID
    shift_id: UUID
    lines: list[POSReceiptLineCreate] = Field(..., min_length=1)
    payments: list[POSPaymentCreate] | None = None


class POSReceiptUpdate(BaseModel):
    status: str | None = Field(None, pattern="^(draft|paid|voided|invoiced)$")
    customer_id: UUID | None = None


class POSReceiptResponse(POSReceiptBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    register_id: UUID
    shift_id: UUID
    cashier_id: UUID | None = None
    number: str
    status: str
    invoice_id: UUID | None = None
    gross_total: Decimal
    tax_total: Decimal
    paid_at: datetime | None = None
    created_at: datetime
    lines: list[POSReceiptLineResponse] = []
    payments: list[POSPaymentResponse] = []


# ==================== INVOICE CONVERSION SCHEMAS ====================
class CustomerDataForInvoice(BaseModel):
    name: str = Field(..., min_length=1)
    tax_id: str = Field(..., min_length=1)
    country: str = Field(..., pattern="^(ES|EC)$")
    address: str | None = None
    email: str | None = None


class ReceiptToInvoiceRequest(BaseModel):
    customer: CustomerDataForInvoice
    series: str | None = None


# ==================== REFUND SCHEMAS ====================
class ReceiptRefundRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)
    refund_method: str = Field(..., pattern="^(cash|card|store_credit)$")
    store_credit_months: int | None = Field(default=12, ge=1, le=24)
