from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import String, Integer, Numeric, JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class SalesOrder(Base):
    __tablename__ = "sales_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    customer_id: Mapped[Optional[int]]
    status: Mapped[str] = mapped_column(String, default="draft")
    currency: Mapped[Optional[str]]
    totals: Mapped[Optional[dict]] = mapped_column(JSON)
    # Avoid reserved attribute name 'metadata' in SQLAlchemy declarative
    extra_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSON)


class SalesOrderItem(Base):
    __tablename__ = "sales_order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    order_id: Mapped[int] = mapped_column(Integer, nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    qty: Mapped[float] = mapped_column(Numeric, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric, default=0)
    tax: Mapped[Optional[dict]] = mapped_column(JSON)
    # Avoid reserved attribute name 'metadata'
    extra_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSON)
