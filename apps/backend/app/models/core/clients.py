"""Module: clients.py

Auto-generated module docstring.

Updated to support multi-tenant UUID via tenants(id) while keeping
legacy empresa_id linkage during transition.
"""
import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
try:  # Postgres UUID if available; fallback to generic for SQLite/tests
    from sqlalchemy.dialects.postgresql import UUID as PGUUID  # type: ignore
except Exception:  # pragma: no cover
    PGUUID = String  # fallback

from app.config.database import Base


class Cliente(Base):
    """Customer entity (scoped by tenant and legacy empresa)."""
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    identificacion: Mapped[str] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, nullable=True)
    telefono: Mapped[str] = mapped_column(String, nullable=True)
    direccion: Mapped[str] = mapped_column(String, nullable=True)
    localidad: Mapped[str] = mapped_column(String, nullable=True)
    provincia: Mapped[str] = mapped_column(String, nullable=True)
    pais: Mapped[str] = mapped_column(String, nullable=True)
    codigo_postal: Mapped[str] = mapped_column(String, nullable=True)

    # Multi-tenant: prefer tenant_id (UUID). empresa_id kept for legacy linkage.
    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("core_empresa.id"), nullable=False)
