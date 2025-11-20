from __future__ import annotations

from uuid import uuid4

from sqlalchemy import JSON, Boolean, String
from sqlalchemy import text as sa_text
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
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        _uuid_col(),
        primary_key=True,
        # Python-side default for tests/SQLite and client-side generation
        default=lambda: uuid4(),
        # Server-side default for Postgres so ORM can fetch RETURNING
        server_default=sa_text("gen_random_uuid()"),
    )
    tenant_id: Mapped[str] = mapped_column(_uuid_col(), index=True)
    code: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    # DB column is 'active' but our model uses 'is_active' in code
    is_active: Mapped[bool] = mapped_column("active", Boolean, default=True, nullable=False)
    # Avoid reserved attribute name 'metadata'
    extra_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
