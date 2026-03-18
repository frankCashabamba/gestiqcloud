"""Module definitions (modules contracted per tenant/user)."""

# pylint: disable=unsubscriptable-object
import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base

# UUID column type (Postgres UUID or String for SQLite)
_uuid_col = PGUUID(as_uuid=True).with_variant(String(36), "sqlite")

# JSONB with SQLite fallback
JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class Module(Base):
    """Module catalog entry — fuente de verdad para todos los módulos del sistema."""

    __tablename__ = "modules"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        _uuid_col, primary_key=True, default=uuid.uuid4, index=True
    )  # type: ignore

    # Identificación
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # canonical ID (ej: "pos")
    description: Mapped[str | None] = mapped_column(Text)  # type: ignore
    icon: Mapped[str | None] = mapped_column(String(100), default="📦")  # type: ignore
    category: Mapped[str | None] = mapped_column(String(50))  # type: ignore

    # Estado
    active: Mapped[bool] = mapped_column(Boolean, default=True)  # type: ignore
    implemented: Mapped[bool] = mapped_column(Boolean, default=True)  # type: ignore

    # Comportamiento
    required: Mapped[bool] = mapped_column(Boolean, default=False)  # type: ignore
    default_enabled: Mapped[bool] = mapped_column(Boolean, default=True)  # type: ignore
    dependencies: Mapped[list | None] = mapped_column(JSON_TYPE)  # IDs de módulos requeridos
    aliases: Mapped[list | None] = mapped_column(JSON_TYPE)  # nombres alternativos reconocidos

    # Disponibilidad geográfica y sectorial
    countries: Mapped[list | None] = mapped_column(JSON_TYPE)  # ["ES", "EC"] o null = todos
    sectors: Mapped[list | None] = mapped_column(JSON_TYPE)  # null = todos los sectores

    # Frontend routing (legacy, mantenido para compatibilidad)
    url: Mapped[str | None] = mapped_column(String(255))  # catalog_id / slug
    initial_template: Mapped[str] = mapped_column(String(255), nullable=False)  # type: ignore
    context_type: Mapped[str] = mapped_column(String(10), default="none")  # type: ignore
    target_model: Mapped[str | None] = mapped_column(String(255))  # type: ignore
    context_filters: Mapped[dict | None] = mapped_column(JSON_TYPE)  # legacy JSONB blob


class CompanyModule(Base):
    """Tenant-purchased module."""

    __tablename__ = "company_modules"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        _uuid_col, primary_key=True, default=uuid.uuid4, index=True
    )  # type: ignore
    tenant_id: Mapped[object] = mapped_column(_uuid_col, ForeignKey("tenants.id"), nullable=False)  # type: ignore
    module_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("modules.id"), nullable=False)  # type: ignore
    active: Mapped[bool] = mapped_column(Boolean, default=True)  # type: ignore
    activation_date: Mapped[datetime] = mapped_column(Date(), default=lambda: datetime.now(UTC))  # type: ignore
    expiration_date: Mapped[datetime | None] = mapped_column(Date())  # type: ignore
    initial_template: Mapped[str | None] = mapped_column(String(255))  # type: ignore

    module: Mapped["Module"] = relationship("Module")  # type: ignore
    tenant: Mapped["Tenant"] = relationship("Tenant", foreign_keys=[tenant_id])  # type: ignore # noqa: F821


class AssignedModule(Base):
    """Class AssignedModule - auto-generated docstring."""

    __tablename__ = "assigned_modules"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "module_id",
            "tenant_id",
            name="assigned_modules_user_id_module_id_tenant_id_uniq",
        ),
        {"extend_existing": True},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        _uuid_col, primary_key=True, default=uuid.uuid4
    )  # pylint: disable=unsubscriptable-object
    tenant_id: Mapped[object] = mapped_column(_uuid_col, ForeignKey("tenants.id"), nullable=True)  # type: ignore
    # CompanyUser.id is UUID; align FK type
    user_id: Mapped[uuid.UUID] = mapped_column(
        _uuid_col, ForeignKey("company_users.id"), nullable=False
    )  # type: ignore
    module_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("modules.id"), nullable=False)  # type: ignore
    assignment_date: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))  # type: ignore
    auto_view_module: Mapped[bool] = mapped_column(Boolean, default=True)  # type: ignore
    module: Mapped["Module"] = relationship("Module", lazy="joined")  # 👈  # type: ignore
