from __future__ import annotations

from typing import Optional

from sqlalchemy import String, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


def _uuid_col():
    try:
        return PGUUID(as_uuid=True)
    except Exception:
        return String


class Delivery(Base):
    __tablename__ = "deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(_uuid_col(), index=True)
    order_id: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending")
    # Avoid reserved attribute name 'metadata'
    extra_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSON)
