"""Modelo de Gastos"""

import uuid
from datetime import date, datetime

from app.config.database import Base
from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Gasto(Base):
    """Gasto operativo"""

    __tablename__ = "gastos"
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
    fecha: Mapped[date] = mapped_column(Date, nullable=False, default=date.today, index=True)
    concepto: Mapped[str] = mapped_column(String(255), nullable=False)
    categoria: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        # nomina, alquiler, suministros, marketing, servicios, otros
    )
    subcategoria: Mapped[str | None] = mapped_column(String(100), nullable=True)
    importe: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    iva: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    proveedor_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("proveedores.id", ondelete="SET NULL"),
        nullable=True,
    )
    forma_pago: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        # efectivo, transferencia, tarjeta, domiciliacion
    )
    factura_numero: Mapped[str | None] = mapped_column(String(100), nullable=True)
    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pendiente",
        index=True,
        # pendiente, pagado, cancelado
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    proveedor = relationship("Proveedor", foreign_keys=[proveedor_id])

    def __repr__(self):
        return f"<Gasto {self.concepto} - {self.total}>"
