from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base

# JSONB with SQLite fallback
JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class Document(Base):
    """Issued document stored as JSON snapshot (MVP persistence)."""

    __tablename__ = "documents"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(5), nullable=False)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    series: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sequential: Mapped[str | None] = mapped_column(String(50), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    template_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    template_version: Mapped[int | None] = mapped_column(nullable=True)
    config_version: Mapped[int | None] = mapped_column(nullable=True)
    config_effective_from: Mapped[str | None] = mapped_column(String(50), nullable=True)
    country_pack_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON_TYPE)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
