"""
Production Cost Driver Models

Indirect cost tracking for production:
- Cost drivers catalog (labor roles, energy, packaging, overhead)
- Recipe standard cost lines (expected costs per recipe)
- Production order actual costs (real costs per batch)
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Computed,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base, schema_column, schema_table_args


class CostDriverUnitType(Base):
    """Catalog of unit types for cost drivers (hour, kwh, unit, flat, etc.)."""

    __tablename__ = "cost_driver_unit_types"
    __table_args__ = schema_table_args()

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    name_es: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()", onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<CostDriverUnitType {self.code} ({self.name_en})>"


class ProductionCostDriver(Base):
    """Catalog of indirect cost types per tenant."""

    __tablename__ = "production_cost_drivers"
    __table_args__ = schema_table_args()

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(30), nullable=False, comment="Unique code per tenant")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="Display name")
    unit: Mapped[str] = mapped_column(
        String(20), nullable=False, default="hour", comment="hour, kwh, unit, flat"
    )
    default_rate: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, default=0, comment="Default cost per unit"
    )
    consumption_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4),
        nullable=True,
        comment="Auto-calc rate (e.g. L/hr for diesel, kWh/hr for electricity)",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()", onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<CostDriver {self.code} ({self.name})>"


class RecipeCostLine(Base):
    """Standard indirect cost line for a recipe."""

    __tablename__ = "recipe_cost_lines"
    __table_args__ = schema_table_args()

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(schema_column("production_cost_drivers"), ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    qty_standard: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, default=0, comment="Standard qty (hours, kwh, etc.)"
    )
    headcount: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="Number of people (for labor)"
    )
    rate_override: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4), nullable=True, comment="Override rate (NULL = use driver default)"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    line_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )

    # Relationships
    driver: Mapped["ProductionCostDriver"] = relationship("ProductionCostDriver", lazy="selectin")

    def __repr__(self):
        return f"<RecipeCostLine recipe={self.recipe_id} driver={self.driver_id}>"


class ProductionOrderCost(Base):
    """Actual indirect cost recorded for a production batch."""

    __tablename__ = "production_order_costs"
    __table_args__ = schema_table_args()

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(schema_column("production_orders"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(schema_column("production_cost_drivers"), ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    qty_actual: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=0)
    headcount_actual: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    rate_applied: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=0)
    cost_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        Computed(
            text("qty_actual * rate_applied * headcount_actual"),
            persisted=True,
        ),
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )

    # Relationships
    driver: Mapped["ProductionCostDriver"] = relationship("ProductionCostDriver", lazy="selectin")

    def __repr__(self):
        return f"<ProductionOrderCost order={self.order_id} cost={self.cost_total}>"
