from __future__ import annotations

import uuid
from sqlalchemy import String, Integer, Numeric, text as sa_text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class StockItem(Base):
    __tablename__ = "stock_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    warehouse_id: Mapped[int] = mapped_column(Integer, nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    qty: Mapped[float] = mapped_column(Numeric, default=0)


class StockMove(Base):
    __tablename__ = "stock_moves"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        # Python-side default for when server func isn't available (e.g., SQLite)
        default=lambda: __import__("uuid").uuid4(),
        # Server-side default for Postgres so ORM inserts don't need to pass id
        server_default=sa_text("gen_random_uuid()"),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    warehouse_id: Mapped[int] = mapped_column(Integer, nullable=False)
    qty: Mapped[float] = mapped_column(Numeric, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    tentative: Mapped[bool] = mapped_column(default=False)
    posted: Mapped[bool] = mapped_column(default=False)
    ref_type: Mapped[str | None]
    ref_id: Mapped[str | None]
