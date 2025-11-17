"""Modelos de Compras"""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class Compra(Base):
    """Orden de compra"""

    __tablename__ = "compras"
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
    proveedor_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("proveedores.id", ondelete="SET NULL"),
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
        # draft, ordered, received, invoiced, cancelled
    )
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_entrega: Mapped[date | None] = mapped_column(Date, nullable=True)
    usuario_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    proveedor = relationship("Proveedor", foreign_keys=[proveedor_id])
    lineas: Mapped[list["CompraLinea"]] = relationship(
        "CompraLinea", back_populates="compra", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Compra {self.numero} - {self.total}>"


class CompraLinea(Base):
    """Línea de orden de compra"""

    __tablename__ = "compra_lineas"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    compra_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("compras.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    producto_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
    )
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    cantidad: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    precio_unitario: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    impuesto_tasa: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False, default=0)
    total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    # Relationships
    compra: Mapped["Compra"] = relationship("Compra", back_populates="lineas")
    producto = relationship("Product", foreign_keys=[producto_id])

    def __repr__(self):
        return f"<CompraLinea {self.description} - {self.cantidad}>"
