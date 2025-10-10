from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    # Use Postgres UUID when available; falls back to generic on SQLite
    try:
        _uuid_col = PGUUID(as_uuid=True)
    except Exception:  # pragma: no cover - SQLite/tests
        _uuid_col = String

    id: Mapped[object] = mapped_column(_uuid_col, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("core_empresa.id"), unique=True, nullable=False)
    slug: Mapped[Optional[str]] = mapped_column(String, unique=True)
    base_currency: Mapped[Optional[str]] = mapped_column(String)
    country_code: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[Optional[datetime]] = mapped_column(default=datetime.utcnow)

    # 1:1 relationship to Empresa (integer PK)
    empresa = relationship("Empresa")

