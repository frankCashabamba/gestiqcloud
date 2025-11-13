"""Modelos de Proveedores"""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class Proveedor(Base):
    """Proveedor (Supplier)"""

    __tablename__ = "proveedores"
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
    codigo: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    nombre_comercial: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tax_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    telefono: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    web: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    contactos: Mapped[List["ProveedorContacto"]] = relationship(
        "ProveedorContacto", back_populates="proveedor", cascade="all, delete-orphan"
    )
    direcciones: Mapped[List["ProveedorDireccion"]] = relationship(
        "ProveedorDireccion", back_populates="proveedor", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Proveedor {self.name}>"


class ProveedorContacto(Base):
    """Contacto de proveedor"""

    __tablename__ = "proveedor_contactos"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    proveedor_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("proveedores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    cargo: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    telefono: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.utcnow
    )

    # Relationships
    proveedor: Mapped["Proveedor"] = relationship(
        "Proveedor", back_populates="contactos"
    )

    def __repr__(self):
        return f"<ProveedorContacto {self.name}>"


class ProveedorDireccion(Base):
    """Dirección de proveedor"""

    __tablename__ = "proveedor_direcciones"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    proveedor_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("proveedores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # fiscal, envio, otro
    direccion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ciudad: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    provincia: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    codigo_postal: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    pais: Mapped[str] = mapped_column(String(2), nullable=False, default="ES")
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.utcnow
    )

    # Relationships
    proveedor: Mapped["Proveedor"] = relationship(
        "Proveedor", back_populates="direcciones"
    )

    def __repr__(self):
        return f"<ProveedorDireccion {self.tipo} - {self.city}>"
