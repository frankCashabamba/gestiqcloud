from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

from pydantic import BaseModel, Field

DocumentType = Literal["TICKET_NO_FISCAL", "FACTURA", "NOTA_VENTA"]
DocumentStatus = Literal["DRAFT", "ISSUED", "VOIDED"]
RenderFormat = Literal["THERMAL_80MM", "A4_PDF"]


class BuyerIn(BaseModel):
    mode: Literal["CONSUMER_FINAL", "IDENTIFIED"]
    idType: str
    idNumber: str | None = None
    name: str | None = None
    email: str | None = None


class SaleItemIn(BaseModel):
    sku: str | None = None
    name: str
    qty: Decimal = Field(gt=0)
    unitPrice: Decimal = Field(ge=0)
    discount: Decimal = Field(default=Decimal("0"))
    taxCategory: str = "DEFAULT"


class PaymentIn(BaseModel):
    method: Literal["CASH", "CARD", "TRANSFER", "OTHER"]
    amount: Decimal = Field(gt=0)


class SaleDraft(BaseModel):
    tenantId: str
    country: str
    posId: str | None = None
    currency: str
    buyer: BuyerIn
    items: list[SaleItemIn] = Field(default_factory=list)
    payments: list[PaymentIn] = Field(default_factory=list)
    meta: dict | None = None


class DocumentInfo(BaseModel):
    id: str
    type: DocumentType
    country: str
    status: DocumentStatus
    issuedAt: datetime | None
    series: str | None
    sequential: str | None
    currency: str
    meta: dict | None = None


class SellerInfo(BaseModel):
    tenantId: str
    tradeName: str
    legalName: str
    taxId: str
    address: str
    logo: str | None = None
    email: str | None = None
    website: str | None = None
    footerMessage: str | None = None


class BuyerInfo(BaseModel):
    mode: Literal["CONSUMER_FINAL", "IDENTIFIED"]
    idType: str
    idNumber: str | None
    name: str | None


class TaxLine(BaseModel):
    tax: str
    rate: Decimal
    amount: Decimal
    code: str


class DocumentLine(BaseModel):
    name: str
    qty: Decimal
    unitPrice: Decimal
    lineSubtotal: Decimal
    taxLines: list[TaxLine]
    lineTotal: Decimal


class Totals(BaseModel):
    subtotal: Decimal
    discount: Decimal
    taxTotal: Decimal
    grandTotal: Decimal


class RenderInfo(BaseModel):
    templateId: str
    templateVersion: int
    format: RenderFormat
    locale: str
    configEffectiveFrom: str | None = None


class DocumentModel(BaseModel):
    document: DocumentInfo
    seller: SellerInfo
    buyer: BuyerInfo
    lines: list[DocumentLine]
    totals: Totals
    payments: list[PaymentIn]
    render: RenderInfo


def _q2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
