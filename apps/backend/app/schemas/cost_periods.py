"""
Schemas Pydantic para Cost Periods (costeo mensual).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CostPeriodBase(BaseModel):
    """Base schema para Cost Period."""
    
    month: str = Field(
        ...,
        pattern=r"^\d{4}-\d{2}$",
        description="Período en formato YYYY-MM (ej: 2025-02)"
    )
    
    # Mano de obra
    labor_hour_rate: float = Field(..., ge=0, description="Tarifa horaria ($/h)")
    labor_paid_hours: float = Field(
        160,
        ge=1,
        description="Horas pagadas en el período (ej: 160 h/mes)"
    )
    touch_hours_total: float | None = Field(
        None,
        ge=0,
        description="Horas reales de trabajo activo medidas (NULL si aún no se mide)"
    )
    
    # Energía
    electricity_cost: float = Field(0, ge=0, description="Costo total de electricidad ($/mes)")
    
    # Diésel
    diesel_cost_month: float = Field(0, ge=0, description="Costo de diésel ($/mes)")
    oven_hours_total: float = Field(160, ge=0.1, description="Horas de horno en el período")
    
    # Configuración avanzada
    production_share_pct: float | None = Field(
        None,
        ge=0,
        le=100,
        description="% de costos asignados a producción (NULL = 100%)"
    )
    
    notes: str | None = Field(None, max_length=500)
    is_active: bool = True

    @field_validator("month")
    @classmethod
    def validate_month(cls, v):
        """Validar que el formato sea correcto y la fecha sea válida."""
        try:
            parts = v.split("-")
            if len(parts) != 2:
                raise ValueError("Formato inválido")
            year = int(parts[0])
            month = int(parts[1])
            if not (1 <= month <= 12):
                raise ValueError("Mes fuera de rango (1-12)")
            if year < 2000 or year > 2100:
                raise ValueError("Año fuera de rango")
        except (ValueError, AttributeError):
            raise ValueError("Formato debe ser YYYY-MM (ej: 2025-02)")
        return v


class CostPeriodCreate(CostPeriodBase):
    """Schema para crear Cost Period."""
    model_config = ConfigDict(extra="forbid")


class CostPeriodUpdate(BaseModel):
    """Schema para actualizar Cost Period."""
    model_config = ConfigDict(extra="forbid")
    
    month: str | None = Field(None, pattern=r"^\d{4}-\d{2}$")
    labor_hour_rate: float | None = Field(None, ge=0)
    labor_paid_hours: float | None = Field(None, ge=1)
    touch_hours_total: float | None = Field(None, ge=0)
    electricity_cost: float | None = Field(None, ge=0)
    diesel_cost_month: float | None = Field(None, ge=0)
    oven_hours_total: float | None = Field(None, ge=0.1)
    production_share_pct: float | None = Field(None, ge=0, le=100)
    notes: str | None = Field(None, max_length=500)
    is_active: bool | None = None


class CostPeriodResponse(CostPeriodBase):
    """Response schema con datos computados."""
    
    id: UUID
    tenant_id: UUID
    
    # Campos computados
    labor_burden_factor: float = Field(
        ...,
        description="COMPUTED: labor_paid_hours / touch_hours_total (si se mide), else 1.0"
    )
    electricity_per_hour: float = Field(
        ...,
        description="COMPUTED: electricity_cost / labor_paid_hours"
    )
    diesel_per_oven_hour: float = Field(
        ...,
        description="COMPUTED: diesel_cost_month / oven_hours_total"
    )
    
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None
    
    model_config = ConfigDict(from_attributes=True)


class CostPeriodDetailResponse(CostPeriodResponse):
    """Response con detalles adicionales."""
    
    # Resumen de cálculos
    total_labor_cost: float = Field(
        ...,
        description="Costo total de nómina (labor_paid_hours * labor_hour_rate)"
    )
    total_indirect_cost: float = Field(
        ...,
        description="electricity_cost + diesel_cost_month"
    )
    total_cost: float = Field(
        ...,
        description="total_labor_cost + total_indirect_cost"
    )
    
    model_config = ConfigDict(from_attributes=True)


class CostPeriodSummary(BaseModel):
    """Resumen para listado."""
    
    id: UUID
    month: str
    labor_hour_rate: float
    labor_paid_hours: float
    electricity_cost: float
    diesel_cost_month: float
    labor_burden_factor: float
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# ANÁLISIS Y VALIDACIÓN
# ============================================================================


class CostPeriodValidationResult(BaseModel):
    """Resultado de validación de un período."""
    
    period_id: UUID
    month: str
    is_valid: bool
    warnings: list[dict] = Field(default_factory=list)
    errors: list[dict] = Field(default_factory=list)
    
    # Checks realizados
    burden_factor_check: bool = Field(
        ...,
        description="TRUE si burden_factor está dentro de rangos esperados (<1.6)"
    )
    oven_utilization_check: bool = Field(
        ...,
        description="TRUE si oven_hours_total es razonables (>10h)"
    )
    touch_hours_check: bool = Field(
        ...,
        description="TRUE si touch_hours_total ≈ labor_paid_hours (eficiencia)"
    )


class CostPeriodRecipeImpact(BaseModel):
    """Impacto de un cost period en una receta."""
    
    recipe_id: UUID
    recipe_name: str
    
    # Costos antes/después de aplicar period
    cost_before: float
    cost_after: float
    cost_change_pct: float
    
    # Desglose
    materials_cost: float
    labor_cost: float
    diesel_cost: float
    electricity_cost: float
    total_cost: float
    unit_cost: float
    
    model_config = ConfigDict(from_attributes=True)
