"""
Milk Record Schemas
"""
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class MilkRecordCreate(BaseModel):
    """Schema para crear registro de leche"""
    fecha: date
    litros: Decimal = Field(gt=0, decimal_places=3)
    grasa_pct: Optional[Decimal] = Field(default=None, ge=0, le=100, decimal_places=2)
    notas: Optional[str] = None
    source_file: Optional[str] = None
    source_row: Optional[int] = None

    @field_validator('litros')
    @classmethod
    def validate_positive(cls, v):
        if v <= 0:
            raise ValueError('Litros debe ser mayor a 0')
        return v

    @field_validator('grasa_pct')
    @classmethod
    def validate_percentage(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Porcentaje de grasa debe estar entre 0 y 100')
        return v


class MilkRecordUpdate(BaseModel):
    """Schema para actualizar registro de leche"""
    fecha: Optional[date] = None
    litros: Optional[Decimal] = Field(default=None, gt=0, decimal_places=3)
    grasa_pct: Optional[Decimal] = Field(default=None, ge=0, le=100, decimal_places=2)
    notas: Optional[str] = None


class MilkRecordResponse(BaseModel):
    """Schema de respuesta para registro de leche"""
    id: UUID
    tenant_id: UUID
    fecha: date
    litros: Decimal
    grasa_pct: Optional[Decimal]
    notas: Optional[str]
    source_file: Optional[str]
    source_row: Optional[int]
    created_at: date

    model_config = {"from_attributes": True}
