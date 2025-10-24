"""
Purchase Schemas
"""
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class PurchaseCreate(BaseModel):
    """Schema para crear compra"""
    fecha: date
    supplier_name: Optional[str] = None
    product_id: Optional[UUID] = None
    cantidad: Decimal = Field(gt=0, decimal_places=3)
    costo_unitario: Decimal = Field(gt=0, decimal_places=4)
    notas: Optional[str] = None
    source_file: Optional[str] = None
    source_row: Optional[int] = None

    @field_validator('cantidad', 'costo_unitario')
    @classmethod
    def validate_positive(cls, v):
        if v <= 0:
            raise ValueError('Debe ser mayor a 0')
        return v


class PurchaseUpdate(BaseModel):
    """Schema para actualizar compra"""
    fecha: Optional[date] = None
    supplier_name: Optional[str] = None
    product_id: Optional[UUID] = None
    cantidad: Optional[Decimal] = Field(default=None, gt=0, decimal_places=3)
    costo_unitario: Optional[Decimal] = Field(default=None, gt=0, decimal_places=4)
    notas: Optional[str] = None


class PurchaseResponse(BaseModel):
    """Schema de respuesta para compra"""
    id: UUID
    tenant_id: UUID
    fecha: date
    supplier_name: Optional[str]
    product_id: Optional[UUID]
    cantidad: Decimal
    costo_unitario: Decimal
    total: Optional[Decimal]
    notas: Optional[str]
    source_file: Optional[str]
    source_row: Optional[int]
    created_at: date

    model_config = {"from_attributes": True}
