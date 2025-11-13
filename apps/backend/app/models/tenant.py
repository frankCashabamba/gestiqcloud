"""Modelo Tenant - Entidad principal multi-tenant.

Consolida la información de empresa (legacy core_empresa) como única fuente de verdad.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Boolean, ForeignKey, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.mutable import MutableDict

from app.config.database import Base


class Tenant(Base):
    """Tenant model - MODERN schema (English names)"""

    __tablename__ = "tenants"
    __table_args__ = {"extend_existing": True}

    # ============================================================
    # PRIMARY KEY - UUID
    # ============================================================
    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )

    # ============================================================
    # BASIC INFORMATION
    # ============================================================
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    slug: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True)

    @property
    def nombre(self) -> str:
        """Legacy property kept for backwards compatibility."""
        return self.name

    @nombre.setter
    def nombre(self, value: str) -> None:
        self.name = value

    # ============================================================
    # TAX & CONTACT DATA
    # ============================================================
    tax_id: Mapped[Optional[str]] = mapped_column(
        String(30), index=True, comment="Tax ID / RUC / NIF / CIF"
    )
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    address: Mapped[Optional[str]] = mapped_column(Text)
    city: Mapped[Optional[str]] = mapped_column(String(100))
    state: Mapped[Optional[str]] = mapped_column(String(100))
    postal_code: Mapped[Optional[str]] = mapped_column(String(20))
    country: Mapped[Optional[str]] = mapped_column(String(100))
    website: Mapped[Optional[str]] = mapped_column(String(255))

    # ============================================================
    # MULTI-TENANT CONFIG
    # ============================================================
    base_currency: Mapped[str] = mapped_column(
        String(3), default="EUR", comment="ISO 4217"
    )
    country_code: Mapped[str] = mapped_column(
        String(2), default="ES", comment="ISO 3166-1 alpha-2"
    )

    # ============================================================
    # BRANDING & CUSTOMIZATION
    # ============================================================
    logo: Mapped[Optional[str]] = mapped_column(
        String(500), comment="Logo URL or path"
    )
    primary_color: Mapped[str] = mapped_column(String(7), default="#4f46e5")
    default_template: Mapped[str] = mapped_column(String(100), default="client")

    # ============================================================
    # SECTOR & TEMPLATE
    # ============================================================
    sector_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    sector_template_name: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )

    # ============================================================
    # JSON CONFIGURATION
    # ============================================================
    config_json: Mapped[Optional[dict]] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True, default=dict
    )

    # ============================================================
    # STATUS & AUDIT
    # ============================================================
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    deactivation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # ============================================================
    # RELATIONSHIPS
    # ============================================================
    incidents: Mapped[List["Incident"]] = relationship(  # noqa: F821
        "Incident", back_populates="tenant", cascade="all, delete-orphan"
    )

    def __repr__(self):
        """String representation."""
        return f"<Tenant {self.name} ({self.country_code})>"

    def __str__(self):
        """Friendly string."""
        return self.name
