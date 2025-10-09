from __future__ import annotations

from typing import Optional

from sqlalchemy import String, Integer, Float, JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


def _uuid_col():
    try:
        return PGUUID(as_uuid=True)
    except Exception:
        return String  # SQLite/tests fallback


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    stock: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String, nullable=False)
    product_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Multitenancy
    tenant_id: Mapped[Optional[str]] = mapped_column(_uuid_col(), nullable=True, index=True)
    sku: Mapped[str] = mapped_column(String, nullable=False)

