"""
HR Payroll Schemas - Esquemas Pydantic para sistema de nóminas

Sistema completo de gestión de nóminas con:
- Cálculo automático de devengos y deducciones
- Compatibilidad España (IRPF, Seg. Social) y Ecuador (IESS, IR)
- Concepts salariales configurables
- Templates de nómina reutilizables
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, validator

# ============================================================================
# CONCEPTOS DE NÓMINA
# ============================================================================


class PayrollConceptBase(BaseModel):
    """Base for payroll concepts (earnings/deductions)."""

    concept_type: str = Field(..., description="EARNING or DEDUCTION")
    code: str = Field(..., max_length=50, description="Concept code")
    description: str = Field(..., max_length=255, description="Readable description")
    amount: Decimal = Field(..., ge=0, description="Concept amount")
    is_base: bool = Field(default=True, description="Counts toward contribution base")

    @validator("concept_type")
    def validate_concept_type(cls, v):
        valid = ["EARNING", "DEDUCTION"]
        if v not in valid:
            raise ValueError(f"concept_type must be one of: {', '.join(valid)}")
        return v

    @validator("code")
    def validate_code(cls, v):
        return v.upper().strip()


class PayrollConceptCreate(PayrollConceptBase):
    """Schema para crear concepto de nómina"""

    pass


class PayrollConceptResponse(PayrollConceptBase):
    """Schema de respuesta para concepto"""

    id: UUID
    payroll_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# PLANTILLAS DE NÓMINA
# ============================================================================


class TemplateConcept(BaseModel):
    """Concept within a template."""

    concept_type: str = Field(..., description="EARNING or DEDUCTION")
    code: str = Field(..., description="Unique code")
    description: str = Field(..., description="Description")
    amount: Decimal = Field(..., ge=0, description="Default amount")
    is_base: bool = Field(default=True)

    @validator("concept_type")
    def validate_concept_type(cls, v):
        valid = ["EARNING", "DEDUCTION"]
        if v not in valid:
            raise ValueError(f"concept_type must be one of: {', '.join(valid)}")
        return v


class PayrollTemplateBase(BaseModel):
    """Base para plantillas de nómina"""

    name: str = Field(..., max_length=100, description="name de la plantilla")
    description: str | None = Field(None, description="Descripción de la plantilla")
    template_concepts: list[TemplateConcept] = Field(
        default_factory=list, description="Lista de concepts estándar"
    )
    is_active: bool = Field(default=True, description="Template activa")


class PayrollTemplateCreate(PayrollTemplateBase):
    """Schema para crear plantilla"""

    employee_id: UUID = Field(..., description="ID del employee")


class PayrollTemplateUpdate(BaseModel):
    """Schema para actualizar plantilla"""

    name: str | None = Field(None, max_length=100)
    description: str | None = None
    template_concepts: list[TemplateConcept] | None = None
    is_active: bool | None = None


class PayrollTemplateResponse(PayrollTemplateBase):
    """Schema de respuesta para plantilla"""

    id: UUID
    tenant_id: UUID
    employee_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# PAYROLLS
# ============================================================================


class PayrollBase(BaseModel):
    """Payroll base schema."""

    employee_id: UUID = Field(..., description="Employee ID")
    period_month: int = Field(..., ge=1, le=12, description="Period month")
    period_year: int = Field(..., ge=2020, le=2100, description="Period year")
    payroll_type: str = Field(default="MONTHLY", description="MONTHLY, BONUS, SEVERANCE, SPECIAL")

    # Devengos
    base_salary: Decimal = Field(default=Decimal("0"), ge=0, description="Base salary")
    allowances: Decimal = Field(default=Decimal("0"), ge=0, description="Allowances")
    overtime_hours: Decimal = Field(default=Decimal("0"), ge=0, description="Overtime hours")
    other_earnings: Decimal = Field(default=Decimal("0"), ge=0, description="Other earnings")

    # Deducciones
    social_security: Decimal = Field(default=Decimal("0"), ge=0, description="Social security/IESS")
    income_tax: Decimal = Field(default=Decimal("0"), ge=0, description="Income tax")
    other_deductions: Decimal = Field(default=Decimal("0"), ge=0, description="Other deductions")

    # Pago
    payment_method: str | None = Field(None, description="cash, transfer, etc.")
    notes: str | None = Field(None, description="Internal notes")

    @validator("payroll_type")
    def validate_payroll_type(cls, v):
        valid = ["MONTHLY", "BONUS", "SEVERANCE", "SPECIAL"]
        if v not in valid:
            raise ValueError(f"payroll_type must be one of: {', '.join(valid)}")
        return v


class PayrollCreate(PayrollBase):
    """Schema para crear nómina"""

    concepts: list[PayrollConceptCreate] | None = Field(
        default_factory=list, description="Concepts adicionales (opcional)"
    )
    auto_calculate: bool = Field(default=True, description="Auto-calcular totales y deducciones")


class PayrollUpdate(BaseModel):
    """Schema para actualizar nómina (solo borrador)"""

    base_salary: Decimal | None = Field(None, ge=0)
    allowances: Decimal | None = Field(None, ge=0)
    overtime_hours: Decimal | None = Field(None, ge=0)
    other_earnings: Decimal | None = Field(None, ge=0)
    social_security: Decimal | None = Field(None, ge=0)
    income_tax: Decimal | None = Field(None, ge=0)
    other_deductions: Decimal | None = Field(None, ge=0)
    payment_method: str | None = None
    notes: str | None = None


class PayrollResponse(PayrollBase):
    """Schema de respuesta para nómina"""

    id: UUID
    tenant_id: UUID
    number: str
    total_earnings: Decimal
    total_deductions: Decimal
    net_total: Decimal
    payment_date: date | None
    status: str
    approved_by: UUID | None
    approved_at: datetime | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime
    concepts: list[PayrollConceptResponse] = []

    class Config:
        from_attributes = True


class PayrollList(BaseModel):
    """Schema para lista paginada de nóminas"""

    items: list[PayrollResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# CALCULADORA DE NÓMINA
# ============================================================================


class PayrollCalculateRequest(BaseModel):
    """Request to calculate payroll."""

    employee_id: UUID = Field(..., description="Employee ID")
    period_month: int = Field(..., ge=1, le=12)
    period_year: int = Field(..., ge=2020, le=2100)
    payroll_type: str = Field(default="MONTHLY")

    # Optional earnings (fallback to employee defaults if omitted)
    base_salary: Decimal | None = Field(None, ge=0)
    allowances: Decimal | None = Field(None, ge=0)
    overtime_hours: Decimal | None = Field(None, ge=0)
    other_earnings: Decimal | None = Field(None, ge=0)

    # Additional concepts
    concepts: list[PayrollConceptCreate] | None = Field(default_factory=list)

    @validator("payroll_type")
    def validate_payroll_type_calc(cls, v):
        valid = ["MONTHLY", "BONUS", "SEVERANCE", "SPECIAL"]
        if v not in valid:
            raise ValueError(f"payroll_type must be one of: {', '.join(valid)}")
        return v


class PayrollCalculateResponse(BaseModel):
    """Payroll calculator response."""

    # Input
    employee_id: UUID
    period_month: int
    period_year: int
    payroll_type: str

    # Earnings
    base_salary: Decimal
    allowances: Decimal
    overtime_hours: Decimal
    other_earnings: Decimal
    total_earnings: Decimal

    # Calculated deductions
    social_security: Decimal
    social_security_rate: Decimal = Field(description="Applied %")
    income_tax: Decimal
    income_tax_rate: Decimal = Field(description="Applied %")
    other_deductions: Decimal
    total_deductions: Decimal

    # Totals
    net_total: Decimal

    # Calculation details
    contribution_base: Decimal = Field(description="Base for social security")
    income_tax_base: Decimal = Field(description="Base for income tax")
    concepts_detail: list[dict[str, Any]] = Field(default_factory=list)

    # Employee info
    employee_name: str
    employee_role: str | None


# ============================================================================
# ACCIONES DE NÓMINA
# ============================================================================


class PayrollApproveRequest(BaseModel):
    """Request to approve payroll."""

    notes: str | None = Field(None, description="Approval notes")


class PayrollPayRequest(BaseModel):
    """Request to mark payroll as paid."""

    payment_date: date = Field(..., description="Actual payment date")
    payment_method: str = Field(..., description="cash, transfer, etc.")
    payment_reference: str | None = Field(None, description="Bank reference")

    @validator("payment_method")
    def validate_metodo(cls, v):
        valid_methods = ["cash", "transfer", "check", "other"]
        if v.lower() not in valid_methods:
            raise ValueError(f"payment_method must be one of: {', '.join(valid_methods)}")
        return v.lower()


# ============================================================================
# ESTADÍSTICAS
# ============================================================================


class PayrollStats(BaseModel):
    """Payroll statistics."""

    # Por status
    total_draft: int
    total_approved: int
    total_paid: int
    total_cancelled: int

    # Current period totals
    total_earnings_mes: Decimal
    total_deductions_mes: Decimal
    total_liquido_mes: Decimal

    # Averages
    promedio_liquido: Decimal

    # Por payroll_type
    payrolls_by_type: dict[str, int] = Field(default_factory=dict)

    # Período
    period_month: int
    period_year: int
    total_empleados: int
    total_payrolls: int


# ============================================================================
# LEGACY ALIASES (compatibilidad con endpoints antiguos)
# ============================================================================

NominaCreate = PayrollCreate
NominaUpdate = PayrollUpdate
NominaResponse = PayrollResponse
NominaList = PayrollList
NominaConceptoCreate = PayrollConceptCreate
NominaCalculateRequest = PayrollCalculateRequest
NominaCalculateResponse = PayrollCalculateResponse
NominaApproveRequest = PayrollApproveRequest
NominaPayRequest = PayrollPayRequest
NominaStats = PayrollStats
