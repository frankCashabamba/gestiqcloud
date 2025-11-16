"""
Finance Caja Schemas - Esquemas Pydantic para gestión de caja

Sistema completo de caja diaria con:
- Movimientos de caja (ingresos/egresos)
- Cierres diarios con conciliación
- Estadísticas y reportes
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, validator

# ============================================================================
# MOVIMIENTOS DE CAJA
# ============================================================================


class CajaMovimientoBase(BaseModel):
    """Base para movimientos de caja"""

    tipo: str = Field(..., description="INGRESO, EGRESO, AJUSTE")
    categoria: str = Field(default="OTRO", description="VENTA, COMPRA, GASTO, NOMINA, BANCO, etc.")
    importe: Decimal = Field(..., description="Importe del movimiento")
    moneda: str = Field(default="EUR", max_length=3, description="Código moneda")
    concepto: str = Field(
        ...,
        max_length=255,
        description="Descripción",
        alias="descripcion",
    )
    notas: str | None = Field(None, description="Notas adicionales")
    fecha: date = Field(default_factory=date.today, description="Fecha del movimiento")
    ref_doc_type: str | None = Field(None, description="Tipo documento origen")
    ref_doc_id: UUID | None = Field(None, description="ID documento origen")
    caja_id: UUID | None = Field(None, description="ID de caja (multi-caja)")

    @validator("tipo")
    def validate_tipo(cls, v):
        if v not in ["INGRESO", "EGRESO", "AJUSTE"]:
            raise ValueError("Tipo debe ser INGRESO, EGRESO o AJUSTE")
        return v

    @validator("categoria")
    def validate_categoria(cls, v):
        valid = ["VENTA", "COMPRA", "GASTO", "NOMINA", "BANCO", "CAMBIO", "AJUSTE", "OTRO"]
        if v not in valid:
            raise ValueError(f'Categoría debe ser una de: {", ".join(valid)}')
        return v

    @validator("importe")
    def validate_importe(cls, v):
        """El importe debe ser positivo."""
        if v <= Decimal("0"):
            raise ValueError("El importe debe ser mayor a cero")
        return v

    @property
    def descripcion(self) -> str:
        return self.concepto

    model_config = ConfigDict(populate_by_name=True)


class CajaMovimientoCreate(CajaMovimientoBase):
    """Schema para crear movimiento de caja"""

    pass


class CajaMovimientoResponse(CajaMovimientoBase):
    """Schema de respuesta para movimiento"""

    id: UUID
    tenant_id: UUID
    usuario_id: UUID | None
    cierre_id: UUID | None
    created_at: datetime

    class Config:
        from_attributes = True


class CajaMovimientoList(BaseModel):
    """Lista paginada de movimientos"""

    items: list[CajaMovimientoResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# CIERRES DE CAJA
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


class CierreCajaBase(BaseModel):
    """Base para cierre de caja"""

    fecha: date = Field(..., description="Fecha del cierre")
    caja_id: UUID | None = Field(None, description="ID de caja")
    moneda: str = Field(default="EUR", max_length=3)
    saldo_inicial: Decimal = Field(default=Decimal("0"), description="Saldo inicial")
    notas: str | None = Field(None, description="Notas del cierre")


class CierreCajaCreate(CierreCajaBase):
    """Schema para crear cierre (apertura de caja)"""

    total_ingresos: Decimal = Field(
        default=Decimal("0"), description="Total de ingresos registrados"
    )
    total_egresos: Decimal = Field(default=Decimal("0"), description="Total de egresos registrados")

    pass


class CierreCajaClose(BaseModel):
    """Schema para cerrar caja"""

    saldo_real: Decimal = Field(..., description="Efectivo contado físicamente")
    detalles_billetes: DetallesBilletes | None = Field(
        None, description="Desglose de billetes y monedas (opcional)"
    )
    notas: str | None = Field(None, description="Notas del cierre")


class CierreCajaResponse(CierreCajaBase):
    """Schema de respuesta para cierre"""

    id: UUID
    tenant_id: UUID
    total_ingresos: Decimal
    total_egresos: Decimal
    saldo_teorico: Decimal
    saldo_real: Decimal
    diferencia: Decimal
    status: str
    cuadrado: bool
    detalles_billetes: dict[str, Any] | None
    abierto_por: UUID | None
    abierto_at: datetime | None
    cerrado_por: UUID | None
    cerrado_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CierreCajaList(BaseModel):
    """Lista paginada de cierres"""

    items: list[CierreCajaResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# SALDO Y ESTADÍSTICAS
# ============================================================================


class CajaSaldoResponse(BaseModel):
    """Respuesta de saldo actual de caja"""

    fecha: date
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
    fecha_desde: date
    fecha_hasta: date
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
