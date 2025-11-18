"""Module: settings.py

Auto-generated module docstring."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class CompanySettings(Base):
    """Class CompanySettings - auto-generated docstring."""

    __tablename__ = "company_settings"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tenant_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id"),
        unique=True,
        index=True,
        nullable=True,
    )

    default_language: Mapped[str] = mapped_column(String(10), default="es")
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    currency: Mapped[str] = mapped_column(String(10), default="USD")

    company_logo: Mapped[str | None] = mapped_column(String(100))
    secondary_color: Mapped[str] = mapped_column(String(7), default="#6c757d")
    primary_color: Mapped[str] = mapped_column(String(7), default="#4f46e5")

    allow_custom_roles: Mapped[bool] = mapped_column(Boolean, default=True)
    user_limit: Mapped[int] = mapped_column(Integer, default=10)

    working_days: Mapped[list[str]] = mapped_column(
        JSON, default=lambda: ["lunes", "martes", "miércoles", "jueves", "viernes"]
    )
    business_hours: Mapped[dict[str, str]] = mapped_column(
        JSON, default=lambda: {"start": "09:00", "end": "18:00"}
    )
    operation_type: Mapped[str] = mapped_column(String, default="ventas")

    company_name: Mapped[str | None] = mapped_column(String)
    tax_id: Mapped[str | None] = mapped_column(String)
    tax_regime: Mapped[str | None] = mapped_column(String)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    language_id: Mapped[int | None] = mapped_column(ForeignKey("languages.id"))
    currency_id: Mapped[int | None] = mapped_column(ForeignKey("currencies.id"))

    tenant = relationship("Tenant", foreign_keys=[tenant_id])


class InventorySettings(Base):
    """Class InventorySettings - auto-generated docstring."""

    __tablename__ = "inventory_settings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tenant_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id"),
        unique=True,
        index=True,
        nullable=True,
    )

    stock_control_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    low_stock_notification_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    global_minimum_stock: Mapped[int | None] = mapped_column(Integer)

    default_units: Mapped[dict | None] = mapped_column(JSON)
    custom_categories_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    extra_product_fields: Mapped[dict | None] = mapped_column(JSON)

    tenant = relationship("Tenant", foreign_keys=[tenant_id])


# Keep old names for backward compatibility during migration
EmpresaSettings = CompanySettings
