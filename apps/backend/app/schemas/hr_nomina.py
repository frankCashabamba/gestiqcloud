"""
HR Nomina Schemas - Esquemas Pydantic para sistema de nóminas

Sistema completo de gestión de nóminas con:
- Cálculo automático de devengos y deducciones
- Compatibilidad España (IRPF, Seg. Social) y Ecuador (IESS, IR)
- Conceptos salariales configurables
- Plantillas de nómina reutilizables
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, validator

# ============================================================================
# CONCEPTOS DE NÓMINA
# ============================================================================


class NominaConceptoBase(BaseModel):
    """Base para conceptos de nómina"""

    tipo: str = Field(..., description="DEVENGO o DEDUCCION")
    codigo: str = Field(..., max_length=50, description="Código del concepto")
    descripcion: str = Field(..., max_length=255, description="Descripción legible")
    importe: Decimal = Field(..., ge=0, description="Importe del concepto")
    es_base: bool = Field(default=True, description="Computa para base de cotización")

    @validator("tipo")
    def validate_tipo(cls, v):
        if v not in ["DEVENGO", "DEDUCCION"]:
            raise ValueError("Tipo debe ser DEVENGO o DEDUCCION")
        return v

    @validator("codigo")
    def validate_codigo(cls, v):
        return v.upper().strip()


class NominaConceptoCreate(NominaConceptoBase):
    """Schema para crear concepto de nómina"""

    pass


class NominaConceptoResponse(NominaConceptoBase):
    """Schema de respuesta para concepto"""

    id: UUID
    nomina_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# PLANTILLAS DE NÓMINA
# ============================================================================


class ConceptoPlantilla(BaseModel):
    """Concepto dentro de una plantilla"""

    tipo: str = Field(..., description="DEVENGO o DEDUCCION")
    codigo: str = Field(..., description="Código único")
    descripcion: str = Field(..., description="Descripción")
    importe: Decimal = Field(..., ge=0, description="Importe por defecto")
    es_base: bool = Field(default=True)

    @validator("tipo")
    def validate_tipo(cls, v):
        if v not in ["DEVENGO", "DEDUCCION"]:
            raise ValueError("Tipo debe ser DEVENGO o DEDUCCION")
        return v


class NominaPlantillaBase(BaseModel):
    """Base para plantillas de nómina"""

    nombre: str = Field(..., max_length=100, description="Nombre de la plantilla")
    descripcion: str | None = Field(None, description="Descripción de la plantilla")
    conceptos_json: list[ConceptoPlantilla] = Field(
        default_factory=list, description="Lista de conceptos estándar"
    )
    activo: bool = Field(default=True, description="Plantilla activa")


class NominaPlantillaCreate(NominaPlantillaBase):
    """Schema para crear plantilla"""

    empleado_id: UUID = Field(..., description="ID del empleado")


class NominaPlantillaUpdate(BaseModel):
    """Schema para actualizar plantilla"""

    nombre: str | None = Field(None, max_length=100)
    descripcion: str | None = None
    conceptos_json: list[ConceptoPlantilla] | None = None
    activo: bool | None = None


class NominaPlantillaResponse(NominaPlantillaBase):
    """Schema de respuesta para plantilla"""

    id: UUID
    tenant_id: UUID
    empleado_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# NÓMINAS
# ============================================================================


class NominaBase(BaseModel):
    """Base para nóminas"""

    empleado_id: UUID = Field(..., description="ID del empleado")
    periodo_mes: int = Field(..., ge=1, le=12, description="Mes del período")
    periodo_ano: int = Field(..., ge=2020, le=2100, description="Año del período")
    tipo: str = Field(default="MENSUAL", description="MENSUAL, EXTRA, FINIQUITO, ESPECIAL")

    # Devengos
    salario_base: Decimal = Field(default=Decimal("0"), ge=0, description="Salario base")
    complementos: Decimal = Field(default=Decimal("0"), ge=0, description="Complementos")
    horas_extra: Decimal = Field(default=Decimal("0"), ge=0, description="Horas extra")
    otros_devengos: Decimal = Field(default=Decimal("0"), ge=0, description="Otros devengos")

    # Deducciones
    seg_social: Decimal = Field(default=Decimal("0"), ge=0, description="Seg. Social/IESS")
    irpf: Decimal = Field(default=Decimal("0"), ge=0, description="IRPF/IR")
    otras_deducciones: Decimal = Field(default=Decimal("0"), ge=0, description="Otras deducciones")

    # Pago
    metodo_pago: str | None = Field(None, description="efectivo, transferencia, etc.")
    notas: str | None = Field(None, description="Notas internas")

    @validator("tipo")
    def validate_tipo(cls, v):
        if v not in ["MENSUAL", "EXTRA", "FINIQUITO", "ESPECIAL"]:
            raise ValueError("Tipo inválido")
        return v


class NominaCreate(NominaBase):
    """Schema para crear nómina"""

    conceptos: list[NominaConceptoCreate] | None = Field(
        default_factory=list, description="Conceptos adicionales (opcional)"
    )
    auto_calculate: bool = Field(default=True, description="Auto-calcular totales y deducciones")


class NominaUpdate(BaseModel):
    """Schema para actualizar nómina (solo borrador)"""

    salario_base: Decimal | None = Field(None, ge=0)
    complementos: Decimal | None = Field(None, ge=0)
    horas_extra: Decimal | None = Field(None, ge=0)
    otros_devengos: Decimal | None = Field(None, ge=0)
    seg_social: Decimal | None = Field(None, ge=0)
    irpf: Decimal | None = Field(None, ge=0)
    otras_deducciones: Decimal | None = Field(None, ge=0)
    metodo_pago: str | None = None
    notas: str | None = None


class NominaResponse(NominaBase):
    """Schema de respuesta para nómina"""

    id: UUID
    tenant_id: UUID
    numero: str
    total_devengado: Decimal
    total_deducido: Decimal
    liquido_total: Decimal
    fecha_pago: date | None
    status: str
    approved_by: UUID | None
    approved_at: datetime | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime
    conceptos: list[NominaConceptoResponse] = []

    class Config:
        from_attributes = True


class NominaList(BaseModel):
    """Schema para lista paginada de nóminas"""

    items: list[NominaResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# CALCULADORA DE NÓMINA
# ============================================================================


class NominaCalculateRequest(BaseModel):
    """Request para calcular nómina"""

    empleado_id: UUID = Field(..., description="ID del empleado")
    periodo_mes: int = Field(..., ge=1, le=12)
    periodo_ano: int = Field(..., ge=2020, le=2100)
    tipo: str = Field(default="MENSUAL")

    # Devengos opcionales (si no se pasan, se usan del empleado)
    salario_base: Decimal | None = Field(None, ge=0)
    complementos: Decimal | None = Field(None, ge=0)
    horas_extra: Decimal | None = Field(None, ge=0)
    otros_devengos: Decimal | None = Field(None, ge=0)

    # Conceptos adicionales
    conceptos: list[NominaConceptoCreate] | None = Field(default_factory=list)

    @validator("tipo")
    def validate_tipo(cls, v):
        if v not in ["MENSUAL", "EXTRA", "FINIQUITO", "ESPECIAL"]:
            raise ValueError("Tipo inválido")
        return v


class NominaCalculateResponse(BaseModel):
    """Respuesta de la calculadora"""

    # Input
    empleado_id: UUID
    periodo_mes: int
    periodo_ano: int
    tipo: str

    # Devengos
    salario_base: Decimal
    complementos: Decimal
    horas_extra: Decimal
    otros_devengos: Decimal
    total_devengado: Decimal

    # Deducciones calculadas
    seg_social: Decimal
    seg_social_rate: Decimal = Field(description="% aplicado")
    irpf: Decimal
    irpf_rate: Decimal = Field(description="% aplicado")
    otras_deducciones: Decimal
    total_deducido: Decimal

    # Total
    liquido_total: Decimal

    # Detalles de cálculo
    base_cotizacion: Decimal = Field(description="Base para Seg. Social")
    base_irpf: Decimal = Field(description="Base para IRPF/IR")
    conceptos_detalle: list[dict[str, Any]] = Field(default_factory=list)

    # Info empleado
    empleado_nombre: str
    empleado_cargo: str | None


# ============================================================================
# ACCIONES DE NÓMINA
# ============================================================================


class NominaApproveRequest(BaseModel):
    """Request para aprobar nómina"""

    notas: str | None = Field(None, description="Notas de aprobación")


class NominaPayRequest(BaseModel):
    """Request para marcar nómina como pagada"""

    fecha_pago: date = Field(..., description="Fecha real de pago")
    metodo_pago: str = Field(..., description="efectivo, transferencia, etc.")
    referencia_pago: str | None = Field(None, description="Referencia bancaria")

    @validator("metodo_pago")
    def validate_metodo(cls, v):
        valid_methods = ["efectivo", "transferencia", "cheque", "otro"]
        if v.lower() not in valid_methods:
            raise ValueError(f"Método debe ser uno de: {', '.join(valid_methods)}")
        return v.lower()


# ============================================================================
# ESTADÍSTICAS
# ============================================================================


class NominaStats(BaseModel):
    """Estadísticas de nóminas"""

    # Por status
    total_draft: int
    total_approved: int
    total_paid: int
    total_cancelled: int

    # Importes período actual
    total_devengado_mes: Decimal
    total_deducido_mes: Decimal
    total_liquido_mes: Decimal

    # Promedio
    promedio_liquido: Decimal

    # Por tipo
    nominas_por_tipo: dict[str, int] = Field(default_factory=dict)

    # Período
    periodo_mes: int
    periodo_ano: int
    total_empleados: int
    total_nominas: int
