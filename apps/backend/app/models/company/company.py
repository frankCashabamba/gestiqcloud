"""Module: company.py

Auto-generated module docstring."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


def _get_now():
    """Get current UTC datetime for Python-side defaults."""
    return datetime.now(UTC)


if TYPE_CHECKING:
    from app.models.company.company_user import CompanyUser


class BusinessType(Base):
    """Business Type model - MODERN schema (English)"""

    __tablename__ = "business_types"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        default=_get_now, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=_get_now, server_default=func.now(), onupdate=_get_now, nullable=False
    )

    # Backward compatibility alias for active -> is_active
    @hybrid_property
    def active(self) -> bool:
        return self.is_active

    @active.setter
    def active(self, value: bool) -> None:
        self.is_active = value


class BusinessCategory(Base):
    """Business Category model - MODERN schema (English)"""

    __tablename__ = "business_categories"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        default=_get_now, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=_get_now, server_default=func.now(), onupdate=_get_now, nullable=False
    )

    # Backward compatibility alias for active -> is_active
    @hybrid_property
    def active(self) -> bool:
        return self.is_active

    @active.setter
    def active(self, value: bool) -> None:
        self.is_active = value


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
    """
    DEPRECATED: Use BusinessCategory instead.

    This model is kept for backward compatibility only.

    BusinessCategory provides:
    - UUID primary key
    - code field (unique identifier)
    - is_active status
    - timestamps (created_at, updated_at)
    - Dedicated endpoint: GET /api/v1/business-categories/

    Deprecation Timeline:
    - Until Q1 2026: Backward compatible, warnings
    - Q1 2026: Will be removed

    Migration: Use BusinessCategory instead
    """

    __tablename__ = "company_categories"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        default=_get_now, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=_get_now, server_default=func.now(), onupdate=_get_now, nullable=False
    )

    # Backward compatibility alias for active -> is_active
    @hybrid_property
    def active(self) -> bool:
        return self.is_active

    @active.setter
    def active(self, value: bool) -> None:
        self.is_active = value


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
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("company_users.id"))
    language: Mapped[str] = mapped_column(String(10), default="es")
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    tenant_id = mapped_column(ForeignKey("tenants.id"))

    user: Mapped["CompanyUser"] = relationship("CompanyUser")
    tenant: Mapped["Tenant"] = relationship("Tenant")  # noqa: F821


class Language(Base):
    """Language catalog model"""

    __tablename__ = "languages"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Currency(Base):
    """Currency model."""

    __tablename__ = "currencies"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol: Mapped[str] = mapped_column(String(5), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Country(Base):
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


class Weekday(Base):
    """Weekday model."""

    __tablename__ = "weekdays"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(50))
    order: Mapped[int] = mapped_column(Integer)


class BusinessHours(Base):
    """Business Hours model."""

    __tablename__ = "business_hours"

    id: Mapped[int] = mapped_column(primary_key=True)
    weekday_id: Mapped[int] = mapped_column(ForeignKey("weekdays.id"))
    start_time: Mapped[str] = mapped_column(String(5), nullable=False)
    end_time: Mapped[str] = mapped_column(String(5), nullable=False)
    weekday: Mapped["Weekday"] = relationship("Weekday")


class SectorTemplate(Base):
    """Sector Template model - MODERN schema (English)"""

    __tablename__ = "sector_templates"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    template_config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        default=_get_now, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=_get_now, server_default=func.now(), onupdate=_get_now, nullable=False
    )
    # Backward compatibility aliases
    @hybrid_property
    def sector_name(self) -> str:
        return self.name

    @sector_name.setter
    def sector_name(self, value: str) -> None:
        self.name = value

    @hybrid_property
    def active(self) -> bool:
        return self.is_active

    @active.setter
    def active(self, value: bool) -> None:
        self.is_active = value

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

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    sector_template_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("sector_templates.id"), nullable=False
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
TipoNegocio = BusinessCategory
SectorPlantilla = SectorTemplate
