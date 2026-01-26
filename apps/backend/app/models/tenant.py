"""Tenant model - primary multi-tenant entity (single source of truth)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base

UUID = PGUUID(as_uuid=True)
TENANT_UUID = UUID.with_variant(String(36), "sqlite")


class Tenant(Base):
    """Tenant model - MODERN schema (English names)"""

    __tablename__ = "tenants"
    __table_args__ = {"extend_existing": True}

    # ============================================================
    # PRIMARY KEY - UUID
    # ============================================================
    id: Mapped[uuid.UUID] = mapped_column(
        TENANT_UUID, primary_key=True, default=uuid.uuid4, nullable=False
    )

    # ============================================================
    # BASIC INFORMATION
    # ============================================================
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    slug: Mapped[str | None] = mapped_column(String(100), unique=True, index=True)

    # ============================================================
    # TAX & CONTACT DATA
    # ============================================================
    tax_id: Mapped[str | None] = mapped_column(
        String(30), index=True, comment="Tax ID / RUC / NIF / CIF"
    )
    phone: Mapped[str | None] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100))
    postal_code: Mapped[str | None] = mapped_column(String(20))
    country: Mapped[str | None] = mapped_column(String(100))
    website: Mapped[str | None] = mapped_column(String(255))

    # ============================================================
    # MULTI-TENANT CONFIG
    # ============================================================
    base_currency: Mapped[str | None] = mapped_column(String(3), nullable=True, comment="ISO 4217")
    country_code: Mapped[str | None] = mapped_column(
        String(2), nullable=True, comment="ISO 3166-1 alpha-2"
    )

    # ============================================================
    # BRANDING & CUSTOMIZATION
    # ============================================================
    logo: Mapped[str | None] = mapped_column(String(500), comment="Logo URL or path")
    primary_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    default_template: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ============================================================
    # SECTOR & TEMPLATE
    # ============================================================
    sector_id: Mapped[int | None] = mapped_column(nullable=True)
    sector_template_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ============================================================
    # JSON CONFIGURATION
    # ============================================================
    config_json: Mapped[dict | None] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True, default=dict
    )

    # ============================================================
    # STATUS & AUDIT
    # ============================================================
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    deactivation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # ============================================================
    # RELATIONSHIPS
    # ============================================================
    incidents: Mapped[list[Incident]] = relationship(  # noqa: F821
        "Incident", back_populates="tenant", cascade="all, delete-orphan"
    )

    def __repr__(self):
        """String representation."""
        return f"<Tenant {self.name} ({self.country_code})>"

    def __str__(self):
        """Friendly string."""
        return self.name
