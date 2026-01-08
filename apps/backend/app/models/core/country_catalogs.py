from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class CountryIdType(Base):
    """Catalog of buyer ID types per country."""

    __tablename__ = "country_id_types"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class CountryTaxCode(Base):
    """Catalog of tax codes per country."""

    __tablename__ = "country_tax_codes"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    rate_default: Mapped[float | None] = mapped_column(Numeric(6, 4), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
