"""
Daily Inventory Schemas
"""
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class DailyInventoryCreate(BaseModel):
    """Schema para crear inventario diario"""
    product_id: UUID
    fecha: date
    stock_inicial: Decimal = Field(ge=0, decimal_places=3)
    venta_unidades: Decimal = Field(default=0, ge=0, decimal_places=3)
    stock_final: Decimal = Field(ge=0, decimal_places=3)
    precio_unitario_venta: Optional[Decimal] = Field(default=None, decimal_places=4)
    source_file: Optional[str] = None
    source_row: Optional[int] = None

    @field_validator('stock_inicial', 'venta_unidades', 'stock_final')
    @classmethod
    def validate_positive(cls, v):
        if v < 0:
            raise ValueError('Debe ser mayor o igual a 0')
        return v


class DailyInventoryUpdate(BaseModel):
    """Schema para actualizar inventario diario"""
    stock_inicial: Optional[Decimal] = Field(default=None, ge=0, decimal_places=3)
    venta_unidades: Optional[Decimal] = Field(default=None, ge=0, decimal_places=3)
    stock_final: Optional[Decimal] = Field(default=None, ge=0, decimal_places=3)
    precio_unitario_venta: Optional[Decimal] = Field(default=None, decimal_places=4)


class DailyInventoryResponse(BaseModel):
    """Schema de respuesta para inventario diario"""
    id: UUID
    tenant_id: UUID
    product_id: UUID
    fecha: date
    stock_inicial: Decimal
    venta_unidades: Decimal
    stock_final: Decimal
    ajuste: Decimal
    precio_unitario_venta: Optional[Decimal]
    importe_total: Optional[Decimal]
    source_file: Optional[str]
    source_row: Optional[int]
    created_at: date

    model_config = {"from_attributes": True}
