"""
Cost Periods Model - Costos indirectos mensuales para prorrateo.

Define los costos indirectos para un período (típicamente mes),
permitiendo recalcular costos de recetas de forma coherente.

Ejemplo para panadería:
    Mes: 2025-02
    - Nómina: 160h @ $4/h = $640
    - Luz: $100
    - Diésel horno: $64
    - Horno disponible: 160h/mes

Con esto se calcula:
    - labor_burden_factor = 160h / touch_hours_total_real (para cubrir tiempos muertos)
    - diesel_per_oven_hour = $64 / 160h = $0.40/h
    - electricity_per_hour = $100 / 160h = $0.625/h
"""

from sqlalchemy import Boolean, Column, DateTime, Index, Numeric, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.config.database import Base as BaseModel


class CostPeriod(BaseModel):
    """
    Período de costeo (mensual típicamente).

    Contiene todos los datos necesarios para calcular costos indirectos
    y prorratearlos entre recetas de forma coherente.
    """

    __tablename__ = "cost_periods"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True, comment="Tenant owner")

    # Período (ej. 2025-02 = febrero 2025)
    month = Column(
        String(7),  # YYYY-MM format
        nullable=False,
        comment="Período en formato YYYY-MM (ej: 2025-02)",
        unique=True,
        index=True,
    )

    # ========== MANO DE OBRA ==========
    labor_hour_rate = Column(
        Numeric(12, 4),
        nullable=False,
        default=0,
        comment="Tarifa por hora de trabajo ($/h). Ej: 4.00",
    )
    labor_paid_hours = Column(
        Numeric(12, 4),
        nullable=False,
        default=160,
        comment="Horas pagadas en el período (ej: 160 h/mes para jornada 8h x 20 días)",
    )
    touch_hours_total = Column(
        Numeric(12, 4),
        nullable=True,
        comment="Horas reales de trabajo activo medidas en el período (NULL si aún no se mide)",
    )
    labor_burden_factor = Column(
        Numeric(8, 4),
        comment="COMPUTED: labor_paid_hours / NULLIF(touch_hours_total, 0) si touch_hours medido, else 1.0",
        server_default=text(
            "CASE WHEN touch_hours_total > 0 "
            "THEN labor_paid_hours / touch_hours_total "
            "ELSE 1.0 END"
        ),
    )

    # ========== ENERGÍA ==========
    electricity_cost = Column(
        Numeric(12, 4),
        nullable=False,
        default=0,
        comment="Costo total de electricidad en el período ($/mes)",
    )
    electricity_per_hour = Column(
        Numeric(12, 4),
        comment="COMPUTED: electricity_cost / labor_paid_hours",
        server_default=text(
            "CASE WHEN labor_paid_hours > 0 "
            "THEN electricity_cost / labor_paid_hours "
            "ELSE 0 END"
        ),
    )

    # ========== DIÉSEL (HORNO) ==========
    diesel_cost_month = Column(
        Numeric(12, 4),
        nullable=False,
        default=0,
        comment="Costo total de diésel en el período ($/mes)",
    )
    oven_hours_total = Column(
        Numeric(12, 4),
        nullable=False,
        default=160,
        comment="Horas reales de funcionamiento del horno en el período",
    )
    diesel_per_oven_hour = Column(
        Numeric(12, 4),
        comment="COMPUTED: diesel_cost_month / NULLIF(oven_hours_total, 0)",
        server_default=text(
            "CASE WHEN oven_hours_total > 0 "
            "THEN diesel_cost_month / oven_hours_total "
            "ELSE 0 END"
        ),
    )

    # ========== CONFIGURACIÓN AVANZADA ==========
    production_share_pct = Column(
        Numeric(5, 2),
        nullable=True,
        default=None,
        comment="% de costos asignados a producción vs tienda (0-100). NULL = 100% a producción",
    )

    # ========== NOTAS Y VALIDACIÓN ==========
    notes = Column(
        String(500),
        nullable=True,
        comment="Notas sobre el período (ej: cambio en tarifa, cortes de luz, etc)",
    )
    is_active = Column(Boolean, default=True, comment="FALSE si el período fue anulado/revertido")

    # ========== AUDITORÍA ==========
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    closed_at = Column(
        DateTime(timezone=True), nullable=True, comment="Fecha/hora del cierre formal del período"
    )

    # Constraints
    __table_args__ = (
        Index("idx_cost_periods_tenant_month", "tenant_id", "month"),
        Index("idx_cost_periods_is_active", "is_active"),
        {"extend_existing": True},
    )

    def __repr__(self):
        return f"<CostPeriod {self.month} labor=${self.labor_hour_rate}/h diesel=${self.diesel_per_oven_hour}/h>"


class CostPeriodValidation(BaseModel):
    """
    Validaciones y advertencias para un CostPeriod.

    Se ejecutan en cierre de período para detectar anomalías.
    """

    __tablename__ = "cost_period_validations"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    period_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    # Tipo de validación
    validation_type = Column(
        String(50),
        nullable=False,
        comment="burden_too_high | oven_underutilized | touch_too_low | etc",
    )
    severity = Column(
        String(20), nullable=False, default="warning", comment="info | warning | error"
    )

    message = Column(String(500), nullable=False)
    suggested_action = Column(String(500), nullable=True)

    is_resolved = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_cost_period_validations_period", "period_id"),
        {"extend_existing": True},
    )

    def __repr__(self):
        return f"<CostPeriodValidation {self.validation_type} ({self.severity})>"
