"""
Accounting Schemas - Esquemas Pydantic para contabilidad

Sistema completo de contabilidad general:
- Plan de cuentas jerárquico
- Asientos contables (libro diario)
- Mayor contable
- Balance de situación
- Cuenta de pérdidas y ganancias
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, validator

# ============================================================================
# PLAN DE CUENTAS
# ============================================================================


class PlanCuentasBase(BaseModel):
    """Base para plan de cuentas"""

    codigo: str = Field(..., max_length=20, description="Código de la cuenta")
    nombre: str = Field(..., max_length=255, description="Nombre de la cuenta")
    descripcion: str | None = Field(None, description="Descripción")
    tipo: str = Field(..., description="ACTIVO, PASIVO, PATRIMONIO, INGRESO, GASTO")
    nivel: int = Field(..., ge=1, le=4, description="Nivel jerárquico")
    padre_id: UUID | None = Field(None, description="ID cuenta padre")
    imputable: bool = Field(default=True, description="Permite movimientos directos")
    activo: bool = Field(default=True, description="Cuenta activa")

    @validator("tipo")
    def validate_tipo(cls, v):
        valid = ["ACTIVO", "PASIVO", "PATRIMONIO", "INGRESO", "GASTO"]
        if v not in valid:
            raise ValueError(f'Tipo debe ser uno de: {", ".join(valid)}')
        return v

    @validator("codigo")
    def validate_codigo(cls, v):
        # Eliminar espacios y convertir a mayúsculas
        return v.strip().upper()


class PlanCuentasCreate(PlanCuentasBase):
    """Schema para crear cuenta"""

    pass


class PlanCuentasUpdate(BaseModel):
    """Schema para actualizar cuenta"""

    nombre: str | None = Field(None, max_length=255)
    descripcion: str | None = None
    activo: bool | None = None
    imputable: bool | None = None


class PlanCuentasResponse(PlanCuentasBase):
    """Schema de respuesta para cuenta"""

    id: UUID
    tenant_id: UUID
    saldo_debe: Decimal
    saldo_haber: Decimal
    saldo: Decimal
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PlanCuentasList(BaseModel):
    """Lista de cuentas"""

    items: list[PlanCuentasResponse]
    total: int


class PlanCuentasTree(BaseModel):
    """Cuenta con jerarquía (árbol)"""

    id: UUID
    codigo: str
    nombre: str
    tipo: str
    nivel: int
    saldo: Decimal
    hijos: list["PlanCuentasTree"] = Field(default_factory=list)


# ============================================================================
# ASIENTOS CONTABLES
# ============================================================================


class AsientoLineaBase(BaseModel):
    """Base para línea de asiento"""

    cuenta_id: UUID = Field(..., description="ID de la cuenta")
    debe: Decimal = Field(default=Decimal("0"), ge=0, description="Importe al debe")
    haber: Decimal = Field(default=Decimal("0"), ge=0, description="Importe al haber")
    descripcion: str | None = Field(None, max_length=255)
    orden: int = Field(default=0, ge=0, description="Orden en el asiento")

    @validator("haber")
    def validate_debe_o_haber(cls, v, values):
        """Solo puede tener debe O haber, no ambos"""
        if "debe" in values:
            if values["debe"] > 0 and v > 0:
                raise ValueError("Una línea solo puede tener debe O haber, no ambos")
            if values["debe"] == 0 and v == 0:
                raise ValueError("Una línea debe tener debe O haber mayor a 0")
        return v


class AsientoLineaCreate(AsientoLineaBase):
    """Schema para crear línea"""

    pass


class AsientoLineaResponse(AsientoLineaBase):
    """Schema de respuesta para línea"""

    id: UUID
    asiento_id: UUID
    created_at: datetime
    cuenta_codigo: str | None = None
    cuenta_nombre: str | None = None

    class Config:
        from_attributes = True


class AsientoContableBase(BaseModel):
    """Base para asiento contable"""

    fecha: date = Field(..., description="Fecha del asiento")
    tipo: str = Field(default="OPERACIONES", description="APERTURA, OPERACIONES, etc.")
    descripcion: str = Field(..., description="Descripción del asiento")
    ref_doc_type: str | None = Field(None, description="Tipo documento origen")
    ref_doc_id: UUID | None = Field(None, description="ID documento origen")

    @validator("tipo")
    def validate_tipo(cls, v):
        valid = ["APERTURA", "OPERACIONES", "REGULARIZACION", "CIERRE"]
        if v not in valid:
            raise ValueError(f'Tipo debe ser uno de: {", ".join(valid)}')
        return v


class AsientoContableCreate(AsientoContableBase):
    """Schema para crear asiento"""

    lineas: list[AsientoLineaCreate] = Field(..., min_items=2, description="Mínimo 2 líneas")

    @validator("lineas")
    def validate_cuadrado(cls, v):
        """Validar que debe = haber"""
        total_debe = sum(l.debe for l in v)
        total_haber = sum(l.haber for l in v)

        if abs(total_debe - total_haber) > Decimal("0.01"):
            raise ValueError(f"El asiento no está cuadrado: Debe={total_debe}, Haber={total_haber}")

        return v


class AsientoContableUpdate(BaseModel):
    """Schema para actualizar asiento (solo borrador)"""

    fecha: date | None = None
    tipo: str | None = None
    descripcion: str | None = None


class AsientoContableResponse(AsientoContableBase):
    """Schema de respuesta para asiento"""

    id: UUID
    tenant_id: UUID
    numero: str
    debe_total: Decimal
    haber_total: Decimal
    cuadrado: bool
    status: str
    created_by: UUID | None
    contabilizado_by: UUID | None
    contabilizado_at: datetime | None
    created_at: datetime
    updated_at: datetime
    lineas: list[AsientoLineaResponse] = []

    class Config:
        from_attributes = True


class AsientoContableList(BaseModel):
    """Lista paginada de asientos"""

    items: list[AsientoContableResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# REPORTES
# ============================================================================


class CuentaMayorItem(BaseModel):
    """Item del libro mayor"""

    fecha: date
    asiento_numero: str
    descripcion: str
    debe: Decimal
    haber: Decimal
    saldo: Decimal


class CuentaMayorResponse(BaseModel):
    """Libro mayor de una cuenta"""

    cuenta_id: UUID
    cuenta_codigo: str
    cuenta_nombre: str
    fecha_desde: date
    fecha_hasta: date
    saldo_inicial: Decimal
    movimientos: list[CuentaMayorItem]
    total_debe: Decimal
    total_haber: Decimal
    saldo_final: Decimal


class BalanceItem(BaseModel):
    """Item del balance"""

    cuenta_id: UUID
    codigo: str
    nombre: str
    nivel: int
    saldo_debe: Decimal
    saldo_haber: Decimal
    saldo: Decimal


class BalanceResponse(BaseModel):
    """Balance de situación"""

    fecha: date
    activos: list[BalanceItem]
    pasivos: list[BalanceItem]
    patrimonio: list[BalanceItem]
    total_activo: Decimal
    total_pasivo: Decimal
    total_patrimonio: Decimal
    cuadrado: bool = Field(description="True si activo = pasivo + patrimonio")


class PyGItem(BaseModel):
    """Item de pérdidas y ganancias"""

    cuenta_id: UUID
    codigo: str
    nombre: str
    nivel: int
    importe: Decimal


class PerdidasGananciasResponse(BaseModel):
    """Cuenta de pérdidas y ganancias"""

    fecha_desde: date
    fecha_hasta: date
    ingresos: list[PyGItem]
    gastos: list[PyGItem]
    total_ingresos: Decimal
    total_gastos: Decimal
    resultado: Decimal = Field(description="Beneficio (positivo) o Pérdida (negativo)")
    resultado_texto: str = Field(description="BENEFICIO o PÉRDIDA")


# ============================================================================
# ESTADÍSTICAS
# ============================================================================


class AccountingStats(BaseModel):
    """Estadísticas contables"""

    # Período
    fecha_desde: date
    fecha_hasta: date

    # Asientos
    total_asientos: int
    asientos_borrador: int
    asientos_validados: int
    asientos_contabilizados: int

    # Cuentas
    total_cuentas: int
    cuentas_activas: int
    cuentas_con_movimientos: int

    # Totales período
    total_debe: Decimal
    total_haber: Decimal

    # Balance
    total_activo: Decimal
    total_pasivo: Decimal
    total_patrimonio: Decimal

    # Resultado
    total_ingresos: Decimal
    total_gastos: Decimal
    resultado_ejercicio: Decimal
