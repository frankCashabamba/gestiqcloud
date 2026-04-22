"""Module: company.py

Auto-generated module docstring."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base
from app.models.base import BaseCatalogModel, BaseCatalogModelWithoutTenant, _get_now

UUID_TYPE = PGUUID(as_uuid=True)
TENANT_UUID = UUID_TYPE.with_variant(String(36), "sqlite")


if TYPE_CHECKING:
    from app.models.company.company_user import CompanyUser


class BusinessType(BaseCatalogModel):
    """Business Type model - MODERN schema (English)"""

    __tablename__ = "business_types"
    __table_args__ = {"extend_existing": True}


class BusinessCategory(BaseCatalogModelWithoutTenant):
    """Business Category model - global config, no tenant isolation"""

    __tablename__ = "business_categories"
    __table_args__ = {"extend_existing": True}


class RolBase(Base):
    """Base Role model"""

    __tablename__ = "base_roles"

    id: Mapped[UUID] = mapped_column(TENANT_UUID, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    permissions: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSON),
        nullable=False,
        default=dict,
    )


# REMOVED: CompanyCategory - DEPRECATED
# Use BusinessCategory instead
# This model was removed to eliminate code duplication and maintenance overhead


class GlobalActionPermission(Base):
    """Global Action Permission model"""

    __tablename__ = "global_action_permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True)
    module: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str] = mapped_column(String(100))


class UserProfile(Base):
    """User Profile model"""

    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(TENANT_UUID, ForeignKey("company_users.id"))
    language: Mapped[str] = mapped_column(String(10), default="es")
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    tenant_id: Mapped[UUID] = mapped_column(TENANT_UUID, ForeignKey("tenants.id"))

    user: Mapped["CompanyUser"] = relationship("CompanyUser")
    tenant: Mapped["Tenant"] = relationship("Tenant")  # noqa: F821


class Language(BaseCatalogModelWithoutTenant):
    """Language catalog model"""

    __tablename__ = "languages"

    id: Mapped[UUID] = mapped_column(TENANT_UUID, primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)


class Currency(BaseCatalogModelWithoutTenant):
    """Currency model."""

    __tablename__ = "currencies"

    id: Mapped[UUID] = mapped_column(TENANT_UUID, primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(5), nullable=False)


class Country(BaseCatalogModelWithoutTenant):
    """Country catalog (ISO 3166-1 alpha-2)."""

    __tablename__ = "countries"

    id: Mapped[UUID] = mapped_column(TENANT_UUID, primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(2), unique=True, nullable=False)


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


class Weekday(BaseCatalogModelWithoutTenant):
    """Weekday model."""

    __tablename__ = "weekdays"

    id: Mapped[UUID] = mapped_column(TENANT_UUID, primary_key=True, default=uuid4)
    key: Mapped[str] = mapped_column(String(20), unique=True)
    order: Mapped[int] = mapped_column(Integer)


class BusinessHours(Base):
    """Business Hours model."""

    __tablename__ = "business_hours"

    id: Mapped[UUID] = mapped_column(TENANT_UUID, primary_key=True, default=uuid4)
    weekday_id: Mapped[UUID] = mapped_column(TENANT_UUID, ForeignKey("weekdays.id"))
    start_time: Mapped[str] = mapped_column(String(5), nullable=False)
    end_time: Mapped[str] = mapped_column(String(5), nullable=False)
    weekday: Mapped["Weekday"] = relationship("Weekday")


class SectorTemplate(BaseCatalogModelWithoutTenant):
    """Sector Template model - global config, no tenant isolation"""

    __tablename__ = "sector_templates"
    __table_args__ = {"extend_existing": True}

    # Additional fields specific to SectorTemplate
    template_config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=True)

    # Backward compatibility aliases
    @hybrid_property
    def sector_name(self) -> str:
        return self.name

    @sector_name.setter
    def sector_name(self, value: str) -> None:
        self.name = value

    # Legacy fields removed from modern schema; keep getters returning None to avoid AttributeError
    @property
    def business_type_id(self):
        return None

    @property
    def business_category_id(self):
        return None

    @property
    def config_version(self) -> int | None:
        # Column may not exist in legacy DBs; expose safe default
        return None


class SectorValidationRule(Base):
    """Sector Validation Rules - MODERN schema (English)

    Stores validation rules for each sector, allowing dynamic validation
    without hardcoding business logic.
    """

    __tablename__ = "sector_validation_rules"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(TENANT_UUID, primary_key=True, default=uuid4)
    sector_template_id: Mapped[UUID] = mapped_column(
        TENANT_UUID, ForeignKey("sector_templates.id"), nullable=False
    )
    context: Mapped[str] = mapped_column(String(50), nullable=False)
    field: Mapped[str] = mapped_column(String(100), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    condition: Mapped[dict] = mapped_column(JSON, nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    level: Mapped[str] = mapped_column(String(20), default="error", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    order: Mapped[int | None] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        default=_get_now, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=_get_now, server_default=func.now(), onupdate=_get_now, nullable=False
    )


# Spanish language aliases for backward compatibility (migration in progress)
Idioma = Language
Moneda = Currency
Pais = Country
DiaSemana = Weekday
HorarioAtencion = BusinessHours
TipoEmpresa = BusinessType
# REMOVED: TipoNegocio = BusinessCategory (was CompanyCategory alias)
SectorPlantilla = SectorTemplate

# Backward compatibility for removed CompanyCategory model
# Use BusinessCategory instead - this provides a smooth migration path
CompanyCategory = BusinessCategory
