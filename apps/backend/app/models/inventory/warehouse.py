from __future__ import annotations

from typing import Optional

from sqlalchemy import String, Boolean, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


def _uuid_col():
    try:
        return PGUUID(as_uuid=True)
    except Exception:
        return String  # SQLite/tests fallback


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(_uuid_col(), index=True)
    code: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

