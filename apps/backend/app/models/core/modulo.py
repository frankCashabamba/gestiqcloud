"""Module: modulo.py

Auto-generated module docstring."""

# pylint: disable=unsubscriptable-object
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property

from app.config.database import Base


# UUID column type (Postgres UUID or String for SQLite)
try:
    _uuid_col = PGUUID(as_uuid=True)
except Exception:  # pragma: no cover (SQLite/tests)
    _uuid_col = String  # type: ignore


class Modulo(Base):
    """Class Modulo - auto-generated docstring."""

    __tablename__ = "modulos_modulo"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)  # type: ignore
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # type: ignore
    description: Mapped[Optional[str]] = mapped_column(Text)  # type: ignore
    active: Mapped[bool] = mapped_column(Boolean, default=True)  # type: ignore
    icono: Mapped[Optional[str]] = mapped_column(String(100), default="📦")  # type: ignore
    url: Mapped[Optional[str]] = mapped_column(String(255))  # type: ignore
    plantilla_inicial: Mapped[str] = mapped_column(String(255), nullable=False)  # type: ignore
    context_type: Mapped[str] = mapped_column(String(10), default="none")  # type: ignore
    modelo_objetivo: Mapped[Optional[str]] = mapped_column(String(255))  # type: ignore
    filtros_contexto: Mapped[Optional[dict]] = mapped_column(JSONB)  # type: ignore
    categoria: Mapped[Optional[str]] = mapped_column(String(50))  # type: ignore


class EmpresaModulo(Base):
    """Class EmpresaModulo - auto-generated docstring."""

    __tablename__ = "modulos_empresamodulo"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)  # type: ignore
    tenant_id: Mapped[object] = mapped_column(
        _uuid_col, ForeignKey("tenants.id"), nullable=False
    )  # type: ignore
    modulo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("modulos_modulo.id"), nullable=False
    )  # type: ignore
    activo: Mapped[bool] = mapped_column(Boolean, default=True)  # type: ignore
    fecha_activacion: Mapped[datetime] = mapped_column(Date, default=datetime.utcnow)  # type: ignore
    fecha_expiracion: Mapped[Optional[datetime]] = mapped_column(Date)  # type: ignore
    plantilla_inicial: Mapped[Optional[str]] = mapped_column(String(255))  # type: ignore

    # Alias en inglés para compatibilidad con código y esquemas
    @hybrid_property
    def active(self) -> bool:  # pragma: no cover - accessor trivial
        return bool(self.activo)

    @active.setter
    def active(self, value: bool) -> None:  # pragma: no cover - setter trivial
        self.activo = bool(value)

    @active.expression  # permite usar .active en filtros SQLAlchemy
    def active(cls):  # type: ignore[no-redef]
        return cls.activo

    modulo: Mapped["Modulo"] = relationship("Modulo")  # type: ignore
    tenant: Mapped["Tenant"] = relationship("Tenant", foreign_keys=[tenant_id])  # type: ignore # noqa: F821


class ModuloAsignado(Base):
    """Class ModuloAsignado - auto-generated docstring."""

    __tablename__ = "modulos_moduloasignado"
    __table_args__ = (
        UniqueConstraint(
            "usuario_id",
            "modulo_id",
            "tenant_id",
            name="modulos_moduloasignado_usuario_id_modulo_id_tenant_id_uniq",
        ),
        {"extend_existing": True},
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # pylint: disable=unsubscriptable-object
    tenant_id: Mapped[object] = mapped_column(
        _uuid_col, ForeignKey("tenants.id"), nullable=True
    )  # type: ignore
    # UsuarioEmpresa.id es UUID; alinear tipo de FK
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        _uuid_col, ForeignKey("usuarios_usuarioempresa.id"), nullable=False
    )  # type: ignore
    modulo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("modulos_modulo.id"), nullable=False
    )  # type: ignore
    fecha_asignacion: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )  # type: ignore
    ver_modulo_auto: Mapped[bool] = mapped_column(Boolean, default=True)  # type: ignore
    modulo: Mapped["Modulo"] = relationship(
        "Modulo", lazy="joined"
    )  # 👈  # type: ignore
