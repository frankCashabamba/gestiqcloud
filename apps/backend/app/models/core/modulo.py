"""Module: modulo.py

Auto-generated module docstring."""

# pylint: disable=unsubscriptable-object
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base

# UUID column type (Postgres UUID or String for SQLite)
try:
    _uuid_col = PGUUID(as_uuid=True)
except Exception:  # pragma: no cover (SQLite/tests)
    _uuid_col = String  # type: ignore

# JSONB with SQLite fallback
JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class Module(Base):
    """Class Module - auto-generated docstring."""

    __tablename__ = "modules"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )  # type: ignore
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # type: ignore
    description: Mapped[str | None] = mapped_column(Text)  # type: ignore
    active: Mapped[bool] = mapped_column(Boolean, default=True)  # type: ignore
    icon: Mapped[str | None] = mapped_column(String(100), default="📦")  # type: ignore
    url: Mapped[str | None] = mapped_column(String(255))  # type: ignore
    initial_template: Mapped[str] = mapped_column(String(255), nullable=False)  # type: ignore
    context_type: Mapped[str] = mapped_column(String(10), default="none")  # type: ignore
    target_model: Mapped[str | None] = mapped_column(String(255))  # type: ignore
    context_filters: Mapped[dict | None] = mapped_column(JSON_TYPE)  # type: ignore
    category: Mapped[str | None] = mapped_column(String(50))  # type: ignore

    @property
    def descripcion(self) -> str | None:
        return self.description

    @descripcion.setter
    def descripcion(self, value: str | None) -> None:
        self.description = value

    @property
    def activo(self) -> bool:
        return bool(self.active)

    @activo.setter
    def activo(self, value: bool) -> None:
        self.active = bool(value)


class CompanyModule(Base):
    """Class CompanyModule - auto-generated docstring."""

    __tablename__ = "company_modules"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )  # type: ignore
    tenant_id: Mapped[object] = mapped_column(_uuid_col, ForeignKey("tenants.id"), nullable=False)  # type: ignore
    module_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("modules.id"), nullable=False)  # type: ignore
    active: Mapped[bool] = mapped_column(Boolean, default=True)  # type: ignore
    activation_date: Mapped[datetime] = mapped_column(Date(), default=datetime.utcnow)  # type: ignore
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
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )  # pylint: disable=unsubscriptable-object
    tenant_id: Mapped[object] = mapped_column(_uuid_col, ForeignKey("tenants.id"), nullable=True)  # type: ignore
    # CompanyUser.id es UUID; alinear tipo de FK
    user_id: Mapped[uuid.UUID] = mapped_column(
        _uuid_col, ForeignKey("company_users.id"), nullable=False
    )  # type: ignore
    module_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("modules.id"), nullable=False)  # type: ignore
    assignment_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)  # type: ignore
    auto_view_module: Mapped[bool] = mapped_column(Boolean, default=True)  # type: ignore
    module: Mapped["Module"] = relationship("Module", lazy="joined")  # 👈  # type: ignore
