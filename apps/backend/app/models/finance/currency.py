"""Exchange Rate & Multi-Currency Models"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import TIMESTAMP, Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base, schema_table_args


class ExchangeRate(Base):
    """
    Tasa de cambio diaria para monedas.

    Attributes:
        from_currency: Moneda origen (EUR, USD, etc)
        to_currency: Moneda destino
        rate_date: Fecha de la tasa
        rate: Tasa de cambio
        source: Fuente de la tasa (ECB, XE, MANUAL, etc)
    """

    __tablename__ = "exchange_rates"
    __table_args__ = (
        UniqueConstraint("from_currency", "to_currency", "rate_date", name="uq_exchange_rate_date"),
        schema_table_args(),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Currency pair
    from_currency: Mapped[str] = mapped_column(
        String(3), nullable=False, index=True, comment="Moneda origen (ISO 4217)"
    )
    to_currency: Mapped[str] = mapped_column(
        String(3), nullable=False, index=True, comment="Moneda destino (ISO 4217)"
    )

    # Date
    rate_date: Mapped[date] = mapped_column(
        Date, nullable=False, index=True, comment="Fecha de la tasa"
    )

    # Rate
    rate: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False, comment="Tasa de cambio")

    # Source
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="MANUAL", comment="ECB, XE, MANUAL, etc"
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()", onupdate=datetime.utcnow
    )
