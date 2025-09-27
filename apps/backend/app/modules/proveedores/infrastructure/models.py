from __future__ import annotations

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class Proveedor(Base):
    __tablename__ = "proveedores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("core_empresa.id"), nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    nombre_comercial: Mapped[str | None] = mapped_column(String(200), nullable=True)
    nif: Mapped[str | None] = mapped_column(String(32), nullable=True)
    pais: Mapped[str | None] = mapped_column(String(3), nullable=True)
    idioma: Mapped[str | None] = mapped_column(String(8), nullable=True)
    tipo_impuesto: Mapped[str | None] = mapped_column(String(32), nullable=True)
    retencion_irpf: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    exento_impuestos: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    regimen_especial: Mapped[str | None] = mapped_column(String(100), nullable=True)

    condiciones_pago: Mapped[str | None] = mapped_column(String(100), nullable=True)
    plazo_pago_dias: Mapped[int | None] = mapped_column(Integer, nullable=True)
    descuento_pronto_pago: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    divisa: Mapped[str | None] = mapped_column(String(3), nullable=True)
    metodo_pago: Mapped[str | None] = mapped_column(String(30), nullable=True)
    iban: Mapped[str | None] = mapped_column(String(34), nullable=True)
    iban_actualizado_por: Mapped[str | None] = mapped_column(String(100), nullable=True)
    iban_actualizado_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    contactos: Mapped[list["ProveedorContact"]] = relationship(
        "ProveedorContact",
        cascade="all, delete-orphan",
        back_populates="proveedor",
    )
    direcciones: Mapped[list["ProveedorAddress"]] = relationship(
        "ProveedorAddress",
        cascade="all, delete-orphan",
        back_populates="proveedor",
    )


class ProveedorContact(Base):
    __tablename__ = "proveedor_contactos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    proveedor_id: Mapped[int] = mapped_column(ForeignKey("proveedores.id", ondelete="CASCADE"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    nombre: Mapped[str | None] = mapped_column(String(120), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notas: Mapped[str | None] = mapped_column(String(255), nullable=True)

    proveedor: Mapped[Proveedor] = relationship("Proveedor", back_populates="contactos")


class ProveedorAddress(Base):
    __tablename__ = "proveedor_direcciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    proveedor_id: Mapped[int] = mapped_column(ForeignKey("proveedores.id", ondelete="CASCADE"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    linea1: Mapped[str] = mapped_column(String(200))
    linea2: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ciudad: Mapped[str | None] = mapped_column(String(100), nullable=True)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    codigo_postal: Mapped[str | None] = mapped_column(String(20), nullable=True)
    pais: Mapped[str | None] = mapped_column(String(3), nullable=True)
    notas: Mapped[str | None] = mapped_column(String(255), nullable=True)

    proveedor: Mapped[Proveedor] = relationship("Proveedor", back_populates="direcciones")
