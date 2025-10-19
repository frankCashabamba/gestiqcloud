"""
POS Schemas - Pydantic models for Point of Sale API
"""
from pydantic import BaseModel, Field, validator
from uuid import UUID
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal


# ============================================================================
# Customer Schemas
# ============================================================================

class CustomerQuick(BaseModel):
    """Captura rápida de cliente para facturación desde POS"""
    name: str = Field(..., min_length=1, max_length=200)
    tax_id: str = Field(..., min_length=5, max_length=30)
    country: str = Field(default="EC", pattern="^(ES|EC)$")
    address: Optional[str] = Field(None, max_length=500)
    email: Optional[str] = None
    phone: Optional[str] = None


# ============================================================================
# Receipt Schemas
# ============================================================================

class ReceiptLineBase(BaseModel):
    """Línea de ticket POS"""
    product_id: UUID
    qty: Decimal = Field(..., gt=0)
    uom: str = Field(default="unit")
    unit_price: Decimal = Field(..., ge=0)
    tax_rate: Decimal = Field(default=Decimal("0.15"))
    discount_pct: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    line_total: Decimal


class ReceiptPaymentBase(BaseModel):
    """Pago de ticket"""
    method: str = Field(..., pattern="^(cash|card|store_credit|link)$")
    amount: Decimal = Field(..., gt=0)
    ref: Optional[str] = None  # Referencia externa (ej. store_credit code)


class ReceiptCreate(BaseModel):
    """Crear nuevo ticket"""
    register_id: UUID
    shift_id: UUID
    number: Optional[str] = None  # Auto-generado si null
    customer_id: Optional[UUID] = None
    lines: List[ReceiptLineBase] = Field(..., min_items=1)
    payments: List[ReceiptPaymentBase] = Field(default_factory=list)
    currency: str = Field(default="USD", pattern="^(USD|EUR)$")
    client_temp_id: Optional[str] = None  # Para idempotencia offline
    metadata: Optional[dict] = Field(default_factory=dict)

    @validator("lines")
    def validate_lines_total(cls, v):
        if not v:
            raise ValueError("El ticket debe tener al menos una línea")
        return v


class ReceiptResponse(BaseModel):
    """Respuesta de ticket creado"""
    id: UUID
    number: str
    status: str
    gross_total: Decimal
    tax_total: Decimal
    currency: str
    created_at: datetime
    invoice_id: Optional[UUID] = None

    class Config:
        from_attributes = True


# ============================================================================
# Invoice Conversion
# ============================================================================

class ReceiptToInvoiceRequest(BaseModel):
    """Convertir ticket a factura"""
    customer: CustomerQuick
    series: Optional[str] = None  # Serie de facturación (ej: "F001")
    send_einvoice: bool = Field(default=False)  # Enviar inmediatamente a SRI/AEAT


class ReceiptToInvoiceResponse(BaseModel):
    """Respuesta de conversión"""
    invoice_id: UUID
    numero: str
    pdf_url: str
    einvoice_status: Optional[str] = None  # Si send_einvoice=true


# ============================================================================
# Refund/Returns
# ============================================================================

class RefundRequest(BaseModel):
    """Solicitud de devolución"""
    refund_method: str = Field(..., pattern="^(cash|card|store_credit)$")
    reason: str = Field(..., min_length=5, max_length=500)
    items: Optional[List[UUID]] = None  # IDs de líneas a devolver (null = todas)
    restock: bool = Field(default=True)  # Reintegrar a stock
    restock_condition: str = Field(default="sellable", pattern="^(sellable|damaged|scrapped)$")


class RefundResponse(BaseModel):
    """Respuesta de devolución"""
    status: str
    refund_amount: Decimal
    store_credit_code: Optional[str] = None  # Si refund_method=store_credit
    store_credit_expires_at: Optional[date] = None
    credit_note_id: Optional[UUID] = None  # ID de abono generado


# ============================================================================
# Store Credits
# ============================================================================

class StoreCreditCreate(BaseModel):
    """Crear vale/crédito"""
    customer_id: Optional[UUID] = None
    currency: str = Field(..., pattern="^(USD|EUR)$")
    amount: Decimal = Field(..., gt=0)
    expires_at: Optional[date] = None
    notes: Optional[str] = None


class StoreCreditResponse(BaseModel):
    """Respuesta de vale"""
    id: UUID
    code: str
    amount_initial: Decimal
    amount_remaining: Decimal
    currency: str
    status: str
    expires_at: Optional[date] = None
    created_at: datetime

    class Config:
        from_attributes = True


class StoreCreditRedeemRequest(BaseModel):
    """Redimir vale"""
    code: str = Field(..., min_length=8, max_length=20)
    amount: Decimal = Field(..., gt=0)


# ============================================================================
# Printing
# ============================================================================

class PrintReceiptRequest(BaseModel):
    """Solicitud de impresión"""
    width: int = Field(default=58, pattern="^(58|80)$")
    format: str = Field(default="html", pattern="^(html|pdf|escpos)$")
    copies: int = Field(default=1, ge=1, le=5)


# ============================================================================
# Doc Series (Numeración)
# ============================================================================

class DocSeriesBase(BaseModel):
    """Serie de documentos"""
    name: str = Field(..., min_length=1, max_length=20)
    doc_type: str = Field(..., pattern="^(R|F|C)$")  # Receipt, Factura, Credit note
    register_id: Optional[UUID] = None  # null = backoffice
    reset_policy: str = Field(default="yearly", pattern="^(yearly|never)$")
    active: bool = Field(default=True)


class DocSeriesCreate(DocSeriesBase):
    """Crear serie"""
    pass


class DocSeriesResponse(DocSeriesBase):
    """Serie con metadata"""
    id: UUID
    tenant_id: UUID
    current_no: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Shift (Turno de Caja)
# ============================================================================

class ShiftOpen(BaseModel):
    """Abrir turno"""
    register_id: UUID
    opening_float: Decimal = Field(default=Decimal("0"), ge=0)


class ShiftClose(BaseModel):
    """Cerrar turno"""
    closing_total: Decimal = Field(..., ge=0)
    notes: Optional[str] = None


class ShiftResponse(BaseModel):
    """Turno de caja"""
    id: UUID
    register_id: UUID
    opened_by: UUID
    opened_at: datetime
    closed_at: Optional[datetime] = None
    opening_float: Decimal
    closing_total: Optional[Decimal] = None
    status: str

    class Config:
        from_attributes = True
