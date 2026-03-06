"""
DailyProductionLog - Historial diario de producción y ventas importado.

Se alimenta desde el importador cuando el usuario guarda una hoja tipo REGISTRO
(PRODUCTO, CANTIDAD, PRECIO UNITARIO VENTA, VENTA DIARIA).
NO afecta el stock actual; es solo historial analítico.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import DATE, TIMESTAMP, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class DailyProductionLog(Base):
    """Un renglón de producción/venta de un día, importado desde hoja REGISTRO."""

    __tablename__ = "daily_production_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    log_date: Mapped[date] = mapped_column(DATE, nullable=False)

    # Nombre tal como viene en la hoja (para búsqueda histórica aunque cambie la receta)
    product_name: Mapped[str] = mapped_column(Text, nullable=False)

    # Vínculos opcionales al catálogo
    recipe_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
    )

    qty_produced: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, default=Decimal("0")
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, default=Decimal("0")
    )
    qty_sold: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=Decimal("0"))

    # qty_leftover y revenue son columnas GENERATED en DB; solo se leen
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("imp_documento.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )

    recipe = relationship("Recipe", foreign_keys=[recipe_id], lazy="noload")

    def __repr__(self):
        return f"<DailyProductionLog {self.log_date} {self.product_name}>"
