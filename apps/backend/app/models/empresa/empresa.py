"""Module: empresa.py

Auto-generated module docstring."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base
from app.models.empresa.usuarioempresa import UsuarioEmpresa


class TipoEmpresa(Base):
    """Business Type model - MODERN schema (English)"""

    __tablename__ = "core_tipoempresa"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class TipoNegocio(Base):
    """Business Category model - MODERN schema (English)"""

    __tablename__ = "core_tiponegocio"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class RolBase(Base):
    """Base Role model"""

    __tablename__ = "base_roles"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    permissions: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSON),
        nullable=False,
        default=dict,
    )


class CompanyCategory(Base):
    """Company Category model"""

    __tablename__ = "company_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


class GlobalActionPermission(Base):
    """Global Action Permission model"""

    __tablename__ = "global_action_permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(String(100))


class UserProfile(Base):
    """User Profile model"""

    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("usuarios_usuarioempresa.id")
    )
    language: Mapped[str] = mapped_column(String(10), default="es")
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    tenant_id = mapped_column(ForeignKey("tenants.id"))

    user: Mapped["UsuarioEmpresa"] = relationship("UsuarioEmpresa")
    tenant: Mapped["Tenant"] = relationship("Tenant")  # noqa: F821


class Language(Base):
    """Language catalog model"""

    __tablename__ = "languages"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Moneda(Base):
    """Class Moneda - auto-generated docstring."""

    __tablename__ = "currencies"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol: Mapped[str] = mapped_column(String(5), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class CoreMoneda(Base):
    """Legacy core_moneda catalog used by configuraciones."""

    __tablename__ = "core_moneda"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, name="codigo")
    name: Mapped[str] = mapped_column(String(100), nullable=False, name="nombre")
    symbol: Mapped[str] = mapped_column(String(5), nullable=False, name="simbolo")
    active: Mapped[bool] = mapped_column(Boolean, default=True, name="activo")


class Pais(Base):
    """Country catalog (ISO 3166-1 alpha-2)."""

    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(2), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class RefTimezone(Base):
    __tablename__ = "timezones"
    name: Mapped[str] = mapped_column(String, primary_key=True)
    display_name: Mapped[str] = mapped_column(String)
    offset_minutes: Mapped[int | None] = mapped_column()
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class RefLocale(Base):
    __tablename__ = "locales"
    code: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class DiaSemana(Base):
    """Class DiaSemana - auto-generated docstring."""

    __tablename__ = "core_dia"
    id: Mapped[int] = mapped_column(primary_key=True)
    clave: Mapped[str] = mapped_column(String(20), unique=True)
    nombre: Mapped[str] = mapped_column(String(50))
    orden: Mapped[int] = mapped_column(Integer)


class HorarioAtencion(Base):
    """Class HorarioAtencion - auto-generated docstring."""

    __tablename__ = "core_horarioatencion"

    id: Mapped[int] = mapped_column(primary_key=True)
    dia_id: Mapped[int] = mapped_column(ForeignKey("core_dia.id"))
    inicio: Mapped[str] = mapped_column(String(5), nullable=False)
    fin: Mapped[str] = mapped_column(String(5), nullable=False)
    dia: Mapped["DiaSemana"] = relationship("DiaSemana")


class SectorPlantilla(Base):
    __tablename__ = "core_sectorplantilla"
    id: Mapped[int] = mapped_column(primary_key=True)
    sector_name: Mapped[str] = mapped_column(String(100), unique=True, name="sector_name")
    business_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("core_tipoempresa.id"), name="business_type_id"
    )
    business_category_id: Mapped[int | None] = mapped_column(
        ForeignKey("core_tiponegocio.id"), name="business_category_id"
    )
    template_config: Mapped[dict] = mapped_column(JSON, default=dict, name="template_config")
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
