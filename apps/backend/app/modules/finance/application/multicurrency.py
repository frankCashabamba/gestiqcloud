"""Multi-currency support with exchange rate management."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID

from app.config.database import Base


class Currency(Base):
    __tablename__ = "currencies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    code = Column(String(3), nullable=False, unique=True)  # ISO 4217: USD, EUR, etc.
    name = Column(String(50), nullable=False)
    symbol = Column(String(5), nullable=False, default="")
    decimal_places = Column(Numeric, default=2)
    is_active = Column(Boolean, default=True)


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    from_currency = Column(String(3), nullable=False)
    to_currency = Column(String(3), nullable=False)
    rate = Column(Numeric(18, 8), nullable=False)
    effective_date = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    source = Column(String(50), default="manual")  # "manual", "api", "ecb"
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    __table_args__ = (
        Index("ix_exchange_rates_tenant_pair", "tenant_id", "from_currency", "to_currency"),
    )
