"""
AccountingPeriod — períodos contables (apertura/cierre/regularización).

Cada tenant gestiona períodos mensuales (year+month). Un asiento cuya fecha caiga
dentro de un período CLOSED es rechazado (`periodo_cerrado`).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import TIMESTAMP, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base, schema_table_args


class AccountingPeriod(Base):
    """Período contable mensual por tenant.

    status: OPEN | CLOSED
    """

    __tablename__ = "accounting_periods"
    __table_args__ = (
        UniqueConstraint("tenant_id", "year", "month", name="uq_accounting_periods_tenant_ym"),
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
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    quarter: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="OPEN", index=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    closed_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )
