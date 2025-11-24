"""
Production Order Models

Plan and execute production based on recipes/BOM:
1. Create production order (planned qty)
2. Reserve raw materials (recipe ingredients)
3. Execute production (consume stock)
4. Produce finished goods (increase stock)
5. Register waste/scrap
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, TIMESTAMP
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base, schema_table_args

production_order_status = SQLEnum(
    "DRAFT",
    "SCHEDULED",
    "IN_PROGRESS",
    "COMPLETED",
    "CANCELLED",
    name="production_order_status",
    create_type=False,
)


class ProductionOrder(Base):
    """
    Production Order - Recipe-based manufacturing plan.

    Attributes:
        order_number: Unique order number (e.g., OP-2025-001)
        recipe_id: Base recipe for the run
        product_id: Finished product to produce
        qty_planned: Planned quantity
        qty_produced: Actual produced quantity
        scheduled_date: Scheduled production date
        started_at: Actual start datetime
        completed_at: Actual completion datetime
        status: Current status
        batch_number: Generated lot number
        notes: Internal notes
        waste_qty: Waste quantity
        waste_reason: Waste reason
    """

    __tablename__ = "production_orders"
    __table_args__ = schema_table_args()

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)

    # Sequential numbering
    order_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique order number (e.g., OP-2025-001)",
    )

    # References
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Base recipe",
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, index=True, comment="Finished product"
    )
    warehouse_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, comment="Warehouse where production happens"
    )

    # Quantities
    qty_planned: Mapped[Decimal] = mapped_column(
        Numeric(14, 3), nullable=False, comment="Planned quantity to produce"
    )
    qty_produced: Mapped[Decimal] = mapped_column(
        Numeric(14, 3), nullable=False, default=0, comment="Actual produced quantity"
    )
    waste_qty: Mapped[Decimal] = mapped_column(
        Numeric(14, 3), nullable=False, default=0, comment="Waste quantity"
    )
    waste_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Waste reason")

    # Dates/times
    scheduled_date: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, comment="Scheduled production date"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, comment="Actual start datetime"
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, comment="Actual completion datetime"
    )

    # Status and batch
    status: Mapped[str] = mapped_column(
        production_order_status,
        nullable=False,
        default="DRAFT",
        index=True,
        comment="Current status",
    )
    batch_number: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True, comment="Generated lot number (e.g., LOT-2025-001)"
    )

    # Additional info
    notes: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Internal production notes"
    )
    metadata_json: Mapped[dict | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=True,
        comment="Additional data (temperature, humidity, etc.)",
    )

    # Audit
    created_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()", onupdate=datetime.utcnow
    )

    # Relaciones
    lines: Mapped[list["ProductionOrderLine"]] = relationship(
        "ProductionOrderLine", back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )

    # Backward compatibility: keep Spanish attribute name
    @property
    def numero(self) -> str:
        return self.order_number

    @numero.setter
    def numero(self, value: str) -> None:
        self.order_number = value


class ProductionOrderLine(Base):
    """
    Production Order Lines - Ingredients consumed.

    Attributes:
        order_id: Parent production order
        ingredient_product_id: Ingredient product
        qty_required: Quantity required by recipe
        qty_consumed: Actual consumed quantity
        unit: Unit of measure (kg, l, units, etc.)
        cost_unit: Ingredient unit cost
        cost_total: Line total cost
        stock_move_id: Generated stock movement (if executed)
    """

    __tablename__ = "production_order_lines"
    __table_args__ = schema_table_args()

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # References
    order_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            ProductionOrder.__table__.c.id,
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    ingredient_product_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, index=True, comment="Ingredient product"
    )
    stock_move_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, comment="Generated stock movement"
    )

    # Quantities
    qty_required: Mapped[Decimal] = mapped_column(
        Numeric(14, 3), nullable=False, comment="Quantity required per recipe"
    )
    qty_consumed: Mapped[Decimal] = mapped_column(
        Numeric(14, 3), nullable=False, default=0, comment="Actual consumed quantity"
    )
    unit: Mapped[str] = mapped_column(
        String(20), nullable=False, default="unit", comment="Unit of measure"
    )

    # Costs
    cost_unit: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, default=0, comment="Unit cost"
    )
    cost_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0, comment="Line total cost"
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )

    # Relationships
    order: Mapped["ProductionOrder"] = relationship(
        "ProductionOrder",
        back_populates="lines",
        lazy="select",
        foreign_keys=[order_id],
    )
