from __future__ import annotations

from uuid import uuid4

from app.config.database import Base
from sqlalchemy import Numeric, String
from sqlalchemy import text as sa_text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column


def _uuid_col():
    try:
        return PGUUID(as_uuid=True)
    except Exception:
        return String


class StockItem(Base):
    """Stock Item model - MODERN schema (English names)"""

    __tablename__ = "stock_items"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        _uuid_col(),
        primary_key=True,
        default=lambda: uuid4(),
        server_default=sa_text("gen_random_uuid()"),
    )
    tenant_id: Mapped[str] = mapped_column(_uuid_col(), index=True)
    warehouse_id: Mapped[str] = mapped_column(_uuid_col(), nullable=False)
    product_id: Mapped[str] = mapped_column(_uuid_col(), nullable=False)
    # DB column is now 'qty' (modernized)
    qty: Mapped[float] = mapped_column("qty", Numeric, default=0)
    location: Mapped[str | None] = mapped_column(String(50), nullable=True)
    lot: Mapped[str | None] = mapped_column(String(100), nullable=True)


class StockMove(Base):
    __tablename__ = "stock_moves"

    id: Mapped[str] = mapped_column(
        _uuid_col(),
        primary_key=True,
        # Python-side default for when server func isn't available (e.g., SQLite)
        default=lambda: __import__("uuid").uuid4(),
        # Server-side default for Postgres so ORM inserts don't need to pass id
        server_default=sa_text("gen_random_uuid()"),
    )
    tenant_id: Mapped[str] = mapped_column(_uuid_col(), index=True)
    product_id: Mapped[str] = mapped_column(_uuid_col(), nullable=False)
    warehouse_id: Mapped[str] = mapped_column(_uuid_col(), nullable=False)
    qty: Mapped[float] = mapped_column(Numeric, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    tentative: Mapped[bool] = mapped_column(default=False)
    posted: Mapped[bool] = mapped_column(default=False)
    ref_type: Mapped[str | None]
    ref_id: Mapped[str | None]
