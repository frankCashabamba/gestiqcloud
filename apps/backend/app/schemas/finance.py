"""Schemas Pydantic para Finanzas (Cajas y Bancos)"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# CAJA MOVIMIENTOS
# ============================================================================


# Base schema
class CajaMovimientoBase(BaseModel):
    """Campos comunes de movimiento de caja"""

    caja_id: UUID = Field(..., description="ID de la caja")
    tipo: str = Field(..., pattern="^(ingreso|egreso)$", description="Tipo de movimiento")
    concepto: str = Field(..., max_length=255, description="Concepto del movimiento")
    monto: float = Field(..., gt=0, description="Monto del movimiento")
    fecha: date = Field(default_factory=date.today)
    metodo_pago: str | None = Field(None, pattern="^(cash|card|transfer|check)$")
    referencia: str | None = Field(
        None, max_length=100, description="Referencia o número de documento"
    )
    categoria_id: UUID | None = Field(None, description="ID de categoría de gasto/ingreso")
    notas: str | None = None


# Create schema
class CajaMovimientoCreate(CajaMovimientoBase):
    """Schema para crear movimiento de caja"""

    pass


# Response schema
class CajaMovimientoResponse(CajaMovimientoBase):
    """Schema de respuesta de movimiento de caja"""

    id: UUID
    tenant_id: UUID
    usuario_id: UUID
    saldo_anterior: float = Field(..., description="Saldo antes del movimiento")
    saldo_actual: float = Field(..., description="Saldo después del movimiento")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# List schema
class CajaMovimientoList(BaseModel):
    """Schema para lista paginada de movimientos de caja"""

    items: list[CajaMovimientoResponse]
    total: int
    page: int = 1
    page_size: int = 100


# ============================================================================
# BANCO MOVIMIENTOS
# ============================================================================


# Base schema
class BancoMovimientoBase(BaseModel):
    """Campos comunes de movimiento bancario"""

    cuenta_bancaria_id: UUID = Field(..., description="ID de la cuenta bancaria")
    tipo: str = Field(
        ...,
        pattern="^(ingreso|egreso|transferencia)$",
        description="Tipo de movimiento",
    )
    concepto: str = Field(..., max_length=255, description="Concepto del movimiento")
    monto: float = Field(..., gt=0, description="Monto del movimiento")
    fecha: date = Field(default_factory=date.today)
    fecha_valor: date | None = Field(None, description="Fecha valor del movimiento")
    referencia: str | None = Field(None, max_length=100, description="Referencia bancaria")
    numero_cheque: str | None = Field(None, max_length=50, description="Número de cheque")
    categoria_id: UUID | None = Field(None, description="ID de categoría de gasto/ingreso")
    estado: str = Field(default="pending", pattern="^(pending|cleared|reconciled|cancelled)$")
    notas: str | None = None


# Create schema
class BancoMovimientoCreate(BancoMovimientoBase):
    """Schema para crear movimiento bancario"""

    pass


# Update schema
class BancoMovimientoUpdate(BaseModel):
    """Schema para actualizar movimiento bancario"""

    concepto: str | None = Field(None, max_length=255)
    monto: float | None = Field(None, gt=0)
    fecha: date | None = None
    fecha_valor: date | None = None
    referencia: str | None = Field(None, max_length=100)
    numero_cheque: str | None = Field(None, max_length=50)
    categoria_id: UUID | None = None
    estado: str | None = Field(None, pattern="^(pending|cleared|reconciled|cancelled)$")
    notas: str | None = None

    model_config = ConfigDict(extra="forbid")


# Response schema
class BancoMovimientoResponse(BancoMovimientoBase):
    """Schema de respuesta de movimiento bancario"""

    id: UUID
    tenant_id: UUID
    usuario_id: UUID
    saldo_anterior: float = Field(..., description="Saldo antes del movimiento")
    saldo_actual: float = Field(..., description="Saldo después del movimiento")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# List schema
class BancoMovimientoList(BaseModel):
    """Schema para lista paginada de movimientos bancarios"""

    items: list[BancoMovimientoResponse]
    total: int
    page: int = 1
    page_size: int = 100
