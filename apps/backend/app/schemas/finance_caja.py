"""
Finance Caja Schemas - Pydantic models for cash management.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ============================================================================
# CASH MOVEMENTS
# ============================================================================


class CashMovementBase(BaseModel):
    """Base schema for cash movements"""

    movement_type: str = Field(..., alias="tipo", description="INCOME, EXPENSE, ADJUSTMENT")
    category: str = Field(
        default="OTHER",
        alias="categoria",
        description="SALE, PURCHASE, EXPENSE, PAYROLL, BANK, CHANGE, ADJUSTMENT, OTHER",
    )
    amount: Decimal = Field(..., alias="importe", description="Movement amount (>0)")
    currency: str = Field(default="EUR", alias="moneda", max_length=3, description="Currency code")
    description: str = Field(
        ...,
        alias="description",
        max_length=255,
        description="Description",
    )
    notes: str | None = Field(None, alias="notas", description="Additional notes")
    date: dt.date = Field(default_factory=dt.date.today, alias="fecha", description="Movement date")
    ref_doc_type: str | None = Field(None, description="Source document type")
    ref_doc_id: UUID | None = Field(None, description="Source document ID")
    cash_box_id: UUID | None = Field(None, alias="caja_id", description="Cash box ID (multi-cash)")

    @field_validator("movement_type")
    @classmethod
    def validate_movement_type(cls, v: str) -> str:
        valid = {"INCOME", "EXPENSE", "ADJUSTMENT"}
        if v not in valid:
            raise ValueError(f"movement_type must be one of: {', '.join(sorted(valid))}")
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        valid = {"SALE", "PURCHASE", "EXPENSE", "PAYROLL", "BANK", "CHANGE", "ADJUSTMENT", "OTHER"}
        if v not in valid:
            raise ValueError(f"category must be one of: {', '.join(sorted(valid))}")
        return v

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Amount must be positive."""
        if v <= Decimal("0"):
            raise ValueError("amount must be greater than zero")
        return v

    model_config = ConfigDict(populate_by_name=True)


class CashMovementCreate(CashMovementBase):
    """Create cash movement"""

    pass


class CashMovementResponse(CashMovementBase):
    """Response schema for cash movement"""

    id: UUID
    tenant_id: UUID
    user_id: UUID | None = Field(None, alias="usuario_id")
    closing_id: UUID | None = Field(None, alias="cierre_id")
    created_at: dt.datetime

    model_config = ConfigDict(from_attributes=True)


class CashMovementList(BaseModel):
    """Paginated list of movements"""

    items: list[CashMovementResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# CASH CLOSINGS
# ============================================================================


class DetallesBilletes(BaseModel):
    """Desglose de billetes y monedas"""

    billete_500: int = Field(default=0, ge=0, description="Cantidad de billetes de 500")
    billete_200: int = Field(default=0, ge=0, description="Cantidad de billetes de 200")
    billete_100: int = Field(default=0, ge=0, description="Cantidad de billetes de 100")
    billete_50: int = Field(default=0, ge=0, description="Cantidad de billetes de 50")
    billete_20: int = Field(default=0, ge=0, description="Cantidad de billetes de 20")
    billete_10: int = Field(default=0, ge=0, description="Cantidad de billetes de 10")
    billete_5: int = Field(default=0, ge=0, description="Cantidad de billetes de 5")
    moneda_2: int = Field(default=0, ge=0, description="Cantidad de monedas de 2€")
    moneda_1: int = Field(default=0, ge=0, description="Cantidad de monedas de 1€")
    moneda_050: int = Field(default=0, ge=0, description="Cantidad de monedas de 0.50€")
    moneda_020: int = Field(default=0, ge=0, description="Cantidad de monedas de 0.20€")
    moneda_010: int = Field(default=0, ge=0, description="Cantidad de monedas de 0.10€")
    moneda_005: int = Field(default=0, ge=0, description="Cantidad de monedas de 0.05€")
    moneda_002: int = Field(default=0, ge=0, description="Cantidad de monedas de 0.02€")
    moneda_001: int = Field(default=0, ge=0, description="Cantidad de monedas de 0.01€")

    def calcular_total(self) -> Decimal:
        """Calcula el total de efectivo contado"""
        total = Decimal("0")
        total += self.billete_500 * Decimal("500")
        total += self.billete_200 * Decimal("200")
        total += self.billete_100 * Decimal("100")
        total += self.billete_50 * Decimal("50")
        total += self.billete_20 * Decimal("20")
        total += self.billete_10 * Decimal("10")
        total += self.billete_5 * Decimal("5")
        total += self.moneda_2 * Decimal("2")
        total += self.moneda_1 * Decimal("1")
        total += self.moneda_050 * Decimal("0.50")
        total += self.moneda_020 * Decimal("0.20")
        total += self.moneda_010 * Decimal("0.10")
        total += self.moneda_005 * Decimal("0.05")
        total += self.moneda_002 * Decimal("0.02")
        total += self.moneda_001 * Decimal("0.01")
        return total


class CashClosingBase(BaseModel):
    """Base schema for cash closing"""

    date: dt.date = Field(..., alias="fecha", description="Closing date")
    cash_box_id: UUID | None = Field(None, alias="caja_id", description="Cash box ID")
    currency: str = Field(default="EUR", alias="moneda", max_length=3)
    opening_balance: Decimal = Field(
        default=Decimal("0"), alias="saldo_inicial", description="Opening balance"
    )
    notes: str | None = Field(None, alias="notas", description="Closing notes")

    model_config = ConfigDict(populate_by_name=True)


class CashClosingCreate(CashClosingBase):
    """Open/start a cash closing day"""

    total_income: Decimal = Field(
        default=Decimal("0"), alias="total_ingresos", description="Total income recorded"
    )
    total_expense: Decimal = Field(
        default=Decimal("0"), alias="total_egresos", description="Total expense recorded"
    )


class CashClosingClose(BaseModel):
    """Close cash box"""

    physical_balance: Decimal = Field(..., alias="saldo_real", description="Counted cash amount")
    bill_breakdown: DetallesBilletes | None = Field(
        None, alias="detalles_billetes", description="Optional bill/coin breakdown"
    )
    notes: str | None = Field(None, alias="notas", description="Closing notes")


class CashClosingResponse(CashClosingBase):
    """Response schema for closing"""

    id: UUID
    tenant_id: UUID
    total_income: Decimal = Field(alias="total_ingresos")
    total_expense: Decimal = Field(alias="total_egresos")
    theoretical_balance: Decimal = Field(alias="saldo_teorico")
    physical_balance: Decimal = Field(alias="saldo_real")
    difference: Decimal = Field(alias="diferencia")
    status: str
    is_balanced: bool = Field(alias="cuadrado")
    bill_breakdown: dict[str, Any] | None = Field(alias="detalles_billetes")
    opened_by: UUID | None = Field(alias="abierto_por")
    opened_at: dt.datetime | None = Field(alias="abierto_at")
    closed_by: UUID | None = Field(alias="cerrado_por")
    closed_at: dt.datetime | None = Field(alias="cerrado_at")
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = ConfigDict(from_attributes=True)


class CashClosingList(BaseModel):
    """Paginated list of closings"""

    items: list[CashClosingResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# SALDO Y ESTADÍSTICAS
# ============================================================================


class CajaSaldoResponse(BaseModel):
    """Respuesta de saldo actual de caja"""

    fecha: dt.date
    moneda: str
    saldo_inicial: Decimal
    total_ingresos_hoy: Decimal
    total_egresos_hoy: Decimal
    saldo_actual: Decimal
    caja_id: UUID | None
    tiene_cierre_abierto: bool


class CajaStats(BaseModel):
    """Estadísticas de caja"""

    # Período
    fecha_desde: dt.date
    fecha_hasta: dt.date
    moneda: str

    # Totales
    total_ingresos: Decimal
    total_egresos: Decimal
    saldo_neto: Decimal

    # Por categoría
    ingresos_por_categoria: dict[str, Decimal] = Field(default_factory=dict)
    egresos_por_categoria: dict[str, Decimal] = Field(default_factory=dict)

    # Promedio diario
    promedio_ingresos_dia: Decimal
    promedio_egresos_dia: Decimal

    # Cierres
    total_cierres: int
    cierres_cuadrados: int
    total_diferencias: Decimal

    # Movimientos
    total_movimientos: int
    total_ingresos_count: int
    total_egresos_count: int


# ============================================================================
# LEGACY ALIASES (compatibilidad con endpoints antiguos)
# ============================================================================

# Movimientos
CajaMovimientoCreate = CashMovementCreate
CajaMovimientoResponse = CashMovementResponse
CajaMovimientoList = CashMovementList

# Cierres
CierreCajaCreate = CashClosingCreate
CierreCajaClose = CashClosingClose
CierreCajaResponse = CashClosingResponse
CierreCajaList = CashClosingList
