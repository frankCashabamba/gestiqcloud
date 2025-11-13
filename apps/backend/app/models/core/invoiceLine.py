"""Module: invoiceLine.py

Auto-generated module docstring."""

from uuid import UUID
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class LineaFactura(Base):
    """Class LineaFactura - auto-generated docstring."""

    __tablename__ = "invoice_lines"  # ✅ CORREGIDO: tabla real en DB
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=lambda: __import__("uuid").uuid4(),
    )
    factura_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("invoices.id")
    )  # ✅ CORREGIDO
    sector: Mapped[str] = mapped_column(String(50))  # "panaderia", "taller", etc

    descripcion: Mapped[str]
    cantidad: Mapped[float]
    precio_unitario: Mapped[float]
    iva: Mapped[float] = mapped_column(default=0)

    __mapper_args__ = {"polymorphic_identity": "base", "polymorphic_on": sector}


class LineaPanaderia(LineaFactura):
    """Class LineaPanaderia - auto-generated docstring."""

    __tablename__ = "lineas_panaderia"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("invoice_lines.id"), primary_key=True
    )  # ✅ CORREGIDO
    tipo_pan: Mapped[str]
    gramos: Mapped[float]

    __mapper_args__ = {"polymorphic_identity": "panaderia"}


class LineaTaller(LineaFactura):
    """Class LineaTaller - auto-generated docstring."""

    __tablename__ = "lineas_taller"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("invoice_lines.id"), primary_key=True
    )  # ✅ CORREGIDO
    repuesto: Mapped[str]
    horas_mano_obra: Mapped[float]
    tarifa: Mapped[float]

    __mapper_args__ = {"polymorphic_identity": "taller"}
