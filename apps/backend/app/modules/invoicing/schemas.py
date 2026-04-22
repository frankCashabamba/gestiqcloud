"""Invoice module Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class InvoiceLineBase(BaseModel):
    description: str = Field(max_length=500)
    quantity: Decimal = Field(gt=0, decimal_places=3)
    unit_price: Decimal = Field(ge=0, decimal_places=4)
    tax_rate: Decimal = Field(default=Decimal("0"), ge=0, le=1, decimal_places=4)
    amount: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)


class BakeryInvoiceLine(InvoiceLineBase):
    sector: Literal["bakery"]
    bread_type: str
    grams: Decimal


class WorkshopInvoiceLine(InvoiceLineBase):
    sector: Literal["workshop"]
    spare_part: str
    labor_hours: Decimal
    rate: Decimal


class PosInvoiceLine(BaseModel):
    sector: Literal["pos"]
    description: str = Field(max_length=500)
    quantity: Decimal = Field(default=Decimal("1"), gt=0, decimal_places=3)
    unit_price: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=4)
    tax_rate: Decimal = Field(default=Decimal("0"), ge=0, le=1, decimal_places=4)
    amount: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)
    pos_receipt_line_id: UUID | None = None


InvoiceLineInput = Annotated[
    BakeryInvoiceLine | WorkshopInvoiceLine | PosInvoiceLine,
    Field(discriminator="sector"),
]


class CustomerInfo(BaseModel):
    id: UUID
    name: str
    email: str | None = None
    tax_id: str | None = None

    model_config = ConfigDict(from_attributes=True)


class InvoiceCreate(BaseModel):
    number: str | None = None
    supplier: str | None = None
    issue_date: str | None = None
    status: str = "draft"
    subtotal: Decimal = Decimal("0")
    tax: Decimal = Decimal("0")
    total: Decimal = Decimal("0")
    customer_id: UUID | None = None
    lines: list[InvoiceLineInput] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class InvoiceUpdate(BaseModel):
    number: str | None = None
    supplier: str | None = None
    issue_date: str | None = None
    status: str | None = None
    subtotal: Decimal | None = None
    tax: Decimal | None = None
    total: Decimal | None = None
    customer_id: UUID | None = None
    lines: list[InvoiceLineInput] | None = None

    model_config = ConfigDict(from_attributes=True)


class InvoiceOut(BaseModel):
    id: UUID
    number: str
    issue_date: str | None = None
    status: str
    subtotal: Decimal | None = None
    tax: Decimal | None = None
    total: Decimal | None = None
    customer: CustomerInfo | None = None
    lines: list[InvoiceLineInput] = Field(default_factory=list)
    source: str | None = None

    model_config = ConfigDict(from_attributes=True)


class InvoiceImportCreate(BaseModel):
    file_name: str
    data: Any
    user_id: int

    model_config = ConfigDict(from_attributes=True)


class InvoiceImportOut(BaseModel):
    id: UUID
    number: str
    supplier: str | None = None
    issue_date: str | None = None
    amount: Decimal | None = None
    status: str

    model_config = ConfigDict(from_attributes=True)
