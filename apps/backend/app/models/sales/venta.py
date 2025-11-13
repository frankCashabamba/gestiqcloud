"""Modelo de Ventas (Pedidos de venta pre-factura)"""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, String, Numeric, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class Venta(Base):
    """Pedido de venta (pre-factura)"""

    __tablename__ = "ventas"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    numero: Mapped[str] = mapped_column(String(50), nullable=False)
    cliente_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    fecha: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    impuestos: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
        # CheckConstraint added in migration
    )
    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    usuario_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    cliente = relationship("Cliente", foreign_keys=[cliente_id])

    def __repr__(self):
        return f"<Venta {self.numero} - {self.total}>"
