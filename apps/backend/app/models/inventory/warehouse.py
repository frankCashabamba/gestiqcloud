from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, String
from sqlalchemy import text as sa_text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

UUID_TYPE = PGUUID(as_uuid=True)
SQLITE_UUID = UUID_TYPE.with_variant(String(36), "sqlite")


class Warehouse(Base):
    __tablename__ = "warehouses"
    __table_args__ = {"extend_existing": True}

    # Override id to use string instead of UUID for warehouses
    id: Mapped[str] = mapped_column(
        SQLITE_UUID,
        primary_key=True,
        # Python-side default for tests/SQLite and client-side generation
        default=lambda: uuid4(),
        # Server-side default for Postgres so ORM can fetch RETURNING
        server_default=sa_text("gen_random_uuid()"),
    )

    # Campos básicos para tenant isolation y timestamps
    tenant_id: Mapped[str] = mapped_column(SQLITE_UUID, nullable=False, index=True)

    # Timestamps para consistencia con otros modelos
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.now(UTC), server_default=sa_text("NOW()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.now(UTC),
        server_default=sa_text("NOW()"),
        onupdate=datetime.now(UTC),
        nullable=False,
    )

    # Additional fields specific to Warehouse
    # DB column is 'active' but our model uses 'is_active' in code
    is_active: Mapped[bool] = mapped_column("active", Boolean, default=True, nullable=False)
    # Avoid reserved attribute name 'metadata'
    extra_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
