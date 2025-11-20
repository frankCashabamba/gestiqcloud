from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class TenantFieldConfig(Base):
    __tablename__ = "tenant_field_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    module: Mapped[str] = mapped_column(String, nullable=False, index=True)
    field: Mapped[str] = mapped_column(String, nullable=False)
    visible: Mapped[bool] = mapped_column(Boolean, default=True)
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    ord: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    label: Mapped[str | None] = mapped_column(Text, nullable=True)
    help: Mapped[str | None] = mapped_column(Text, nullable=True)


class SectorFieldDefault(Base):
    __tablename__ = "sector_field_defaults"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sector: Mapped[str] = mapped_column(String, nullable=False, index=True)
    module: Mapped[str] = mapped_column(String, nullable=False, index=True)
    field: Mapped[str] = mapped_column(String, nullable=False)
    visible: Mapped[bool] = mapped_column(Boolean, default=True)
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    ord: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    label: Mapped[str | None] = mapped_column(Text, nullable=True)
    help: Mapped[str | None] = mapped_column(Text, nullable=True)
