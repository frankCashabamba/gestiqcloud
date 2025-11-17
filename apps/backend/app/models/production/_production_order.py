"""
Production Order Models - Órdenes de Producción

Sistema de planificación y ejecución de producción basado en recetas.

Flujo:
1. Crear orden de producción (cantidad a producir)
2. Reservar materias primas (ingredientes de receta)
3. Ejecutar producción (consumo real de stock)
4. Generar productos terminados (aumentar stock)
5. Registrar mermas y desperdicios

Compatible con:
- Panadería: Horneadas de pan/bollería
- Restaurante: Preparaciones de platos/menús
- Otros sectores con recetas/BOM
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

# Enum de estados
production_order_status = SQLEnum(
    "DRAFT",  # Borrador (planificación)
    "SCHEDULED",  # Programado
    "IN_PROGRESS",  # En proceso
    "COMPLETED",  # Completado
    "CANCELLED",  # Cancelado
    name="production_order_status",
    create_type=False,  # No crear tipo si ya existe
)


class ProductionOrder(Base):
    """
    Orden de Producción - Planificación de fabricación basada en recetas.

    Attributes:
        numero: Número único de orden (ej: OP-2025-001)
        recipe_id: Receta base para la producción
        product_id: Producto final a producir
        qty_planned: Cantidad planificada a producir
        qty_produced: Cantidad real producida
        scheduled_date: Fecha programada de producción
        started_at: Fecha/hora inicio real
        completed_at: Fecha/hora finalización real
        status: Estado actual (draft/scheduled/in_progress/completed/cancelled)
        batch_number: Número de lote generado
        notes: Notas internas
        waste_qty: Cantidad de mermas/desperdicios
        waste_reason: Motivo de las mermas
    """

    __tablename__ = "production_orders"
    __table_args__ = schema_table_args()

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)

    # Numeración secuencial
    numero: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="Número único de orden (ej: OP-2025-001)",
    )

    # Referencias
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Receta base",
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, index=True, comment="Producto final"
    )
    warehouse_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, comment="Almacén donde se produce"
    )

    # Cantidades
    qty_planned: Mapped[Decimal] = mapped_column(
        Numeric(14, 3), nullable=False, comment="Cantidad planificada a producir"
    )
    qty_produced: Mapped[Decimal] = mapped_column(
        Numeric(14, 3), nullable=False, default=0, comment="Cantidad real producida"
    )
    waste_qty: Mapped[Decimal] = mapped_column(
        Numeric(14, 3), nullable=False, default=0, comment="Cantidad de mermas/desperdicios"
    )
    waste_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Motivo de las mermas"
    )

    # Fechas y tiempos
    scheduled_date: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, comment="Fecha programada de producción"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, comment="Fecha/hora de inicio real"
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, comment="Fecha/hora de finalización real"
    )

    # Estado y lote
    status: Mapped[str] = mapped_column(
        production_order_status,
        nullable=False,
        default="DRAFT",
        index=True,
        comment="Estado actual",
    )
    batch_number: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True, comment="Número de lote generado (ej: LOT-2025-001)"
    )

    # Información adicional
    notes: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Notas internas de producción"
    )
    metadata_json: Mapped[dict | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=True,
        comment="Datos adicionales (temperatura, humedad, etc.)",
    )

    # Auditoría
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


class ProductionOrderLine(Base):
    """
    Líneas de Orden de Producción - Ingredientes consumidos.

    Cada línea representa un ingrediente de la receta y su consumo real.

    Attributes:
        order_id: Orden de producción padre
        ingredient_product_id: Producto ingrediente
        qty_required: Cantidad requerida según receta
        qty_consumed: Cantidad real consumida
        unit: Unidad de medida (kg, l, units, etc.)
        cost_unit: Costo unitario del ingrediente
        cost_total: Costo total de la línea
        stock_move_id: Movimiento de stock generado (si se ejecutó)
    """

    __tablename__ = "production_order_lines"
    __table_args__ = schema_table_args()

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Referencias
    order_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("production_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ingredient_product_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, index=True, comment="Producto ingrediente"
    )
    stock_move_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, comment="Movimiento de stock generado"
    )

    # Cantidades
    qty_required: Mapped[Decimal] = mapped_column(
        Numeric(14, 3), nullable=False, comment="Cantidad requerida según receta"
    )
    qty_consumed: Mapped[Decimal] = mapped_column(
        Numeric(14, 3), nullable=False, default=0, comment="Cantidad real consumida"
    )
    unit: Mapped[str] = mapped_column(
        String(20), nullable=False, default="unit", comment="Unidad de medida"
    )

    # Costos
    cost_unit: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, default=0, comment="Costo unitario"
    )
    cost_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0, comment="Costo total de la línea"
    )

    # Auditoría
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )

    # Relaciones
    order: Mapped["ProductionOrder"] = relationship(
        "ProductionOrder", back_populates="lines", lazy="select"
    )
