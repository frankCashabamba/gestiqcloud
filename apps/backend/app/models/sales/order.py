from __future__ import annotations

from sqlalchemy import JSON, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


def _uuid_col():
    try:
        return PGUUID(as_uuid=True)
    except Exception:
        return String


class SalesOrder(Base):
    __tablename__ = "sales_orders"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(_uuid_col(), index=True)
    customer_id: Mapped[int | None]
    status: Mapped[str] = mapped_column(String, default="draft")
    currency: Mapped[str | None]
    totals: Mapped[dict | None] = mapped_column("total", JSON)
    # Avoid reserved attribute name 'metadata' in SQLAlchemy declarative
    extra_metadata: Mapped[dict | None] = mapped_column("metadata", JSON)


class SalesOrderItem(Base):
    __tablename__ = "sales_order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(_uuid_col(), index=True)
    order_id: Mapped[int] = mapped_column(Integer, nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    qty: Mapped[float] = mapped_column(Numeric, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric, default=0)
    tax: Mapped[dict | None] = mapped_column(JSON)
    # Avoid reserved attribute name 'metadata'
    extra_metadata: Mapped[dict | None] = mapped_column("metadata", JSON)
