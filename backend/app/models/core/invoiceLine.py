"""Module: invoiceLine.py

Auto-generated module docstring."""

from sqlalchemy import  ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class LineaFactura(Base):
    """ Class LineaFactura - auto-generated docstring. """
    __tablename__ = "invoice_line"

    id: Mapped[int] = mapped_column(primary_key=True)
    factura_id: Mapped[int] = mapped_column(ForeignKey("facturas.id"))
    sector: Mapped[str] = mapped_column(String(50))  # "panaderia", "taller", etc

    descripcion: Mapped[str]
    cantidad: Mapped[float]
    precio_unitario: Mapped[float]
    iva: Mapped[float] = mapped_column(default=0)
    

    __mapper_args__ = {
        "polymorphic_identity": "base",
        "polymorphic_on": sector
    }


class LineaPanaderia(LineaFactura):
    """ Class LineaPanaderia - auto-generated docstring. """
    __tablename__ = "lineas_panaderia"

    id: Mapped[int] = mapped_column(ForeignKey("invoice_line.id"), primary_key=True)
    tipo_pan: Mapped[str]
    gramos: Mapped[float]

    __mapper_args__ = {
        "polymorphic_identity": "panaderia"
    }


class LineaTaller(LineaFactura):
    """ Class LineaTaller - auto-generated docstring. """
    __tablename__ = "lineas_taller"

    id: Mapped[int] = mapped_column(ForeignKey("invoice_line.id"), primary_key=True)
    repuesto: Mapped[str]
    horas_mano_obra: Mapped[float]
    tarifa: Mapped[float]

    __mapper_args__ = {
        "polymorphic_identity": "taller"
    }
