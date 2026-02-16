from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base

UUID = PGUUID(as_uuid=True)

from sqlalchemy import String as _String  # noqa: E402

TENANT_UUID = PGUUID(as_uuid=True).with_variant(_String(36), "sqlite")


class ProfitSnapshotDaily(Base):
    __tablename__ = "profit_snapshots_daily"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        TENANT_UUID, ForeignKey("tenants.id"), nullable=False, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    location_id: Mapped[uuid.UUID | None] = mapped_column(UUID, nullable=True)
    total_sales: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    total_cogs: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    gross_profit: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    total_expenses: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    net_profit: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    order_count: Mapped[int] = mapped_column(Integer, default=0)
    item_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "date", "location_id", name="uq_profit_snap_tenant_date_loc"
        ),
        Index("ix_profit_snapshots_daily_tenant_date", "tenant_id", "date"),
    )


class ProductProfitSnapshot(Base):
    __tablename__ = "product_profit_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        TENANT_UUID, ForeignKey("tenants.id"), nullable=False, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("products.id"), nullable=False
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(UUID, nullable=True)
    revenue: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    cogs: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    gross_profit: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    margin_pct: Mapped[float] = mapped_column(Numeric(6, 2), default=0)
    sold_qty: Mapped[float] = mapped_column(Numeric(14, 3), default=0)
    waste_qty: Mapped[float] = mapped_column(Numeric(14, 3), default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "date", "product_id", "location_id",
            name="uq_prod_snap_tenant_date_prod_loc",
        ),
        Index(
            "ix_product_profit_snapshots_tenant_date_product",
            "tenant_id", "date", "product_id",
        ),
    )
