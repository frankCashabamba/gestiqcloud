from __future__ import annotations

from sqlalchemy import String, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


def _uuid_col():
    try:
        return PGUUID(as_uuid=True)
    except Exception:
        return String


class StockItem(Base):
    __tablename__ = "stock_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(_uuid_col(), index=True)
    warehouse_id: Mapped[int] = mapped_column(Integer, nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    qty: Mapped[float] = mapped_column(Numeric, default=0)


class StockMove(Base):
    __tablename__ = "stock_moves"

    id: Mapped[str] = mapped_column(_uuid_col(), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(_uuid_col(), index=True)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    warehouse_id: Mapped[int] = mapped_column(Integer, nullable=False)
    qty: Mapped[float] = mapped_column(Numeric, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    tentative: Mapped[bool] = mapped_column(default=False)
    ref_type: Mapped[str | None]
    ref_id: Mapped[str | None]

