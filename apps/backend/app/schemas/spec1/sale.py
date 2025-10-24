"""
Sale Schemas
"""
from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SaleLineCreate(BaseModel):
    """Schema para crear línea de venta"""
    product_id: UUID
    qty: Decimal = Field(gt=0, decimal_places=3)
    price: Decimal = Field(ge=0, decimal_places=4)
    tax_pct: Decimal = Field(default=0, ge=0, decimal_places=4)


class SaleLineResponse(BaseModel):
    """Schema de respuesta para línea de venta"""
    id: UUID
    sale_id: UUID
    product_id: UUID
    qty: Decimal
    price: Decimal
    tax_pct: Decimal
    total_line: Decimal
    created_at: date

    model_config = {"from_attributes": True}


class SaleHeaderCreate(BaseModel):
    """Schema para crear venta"""
    fecha: date
    customer_id: Optional[UUID] = None
    customer_name: str = "Consumidor Final"
    payment_method: str = "Efectivo"
    lines: List[SaleLineCreate]
    sale_uuid: Optional[UUID] = None
    pos_receipt_id: Optional[UUID] = None


class SaleHeaderResponse(BaseModel):
    """Schema de respuesta para venta"""
    id: UUID
    tenant_id: UUID
    fecha: date
    customer_id: Optional[UUID]
    customer_name: str
    total: Decimal
    total_tax: Decimal
    payment_method: str
    sale_uuid: Optional[UUID]
    pos_receipt_id: Optional[UUID]
    created_at: date
    lines: List[SaleLineResponse]

    model_config = {"from_attributes": True}
