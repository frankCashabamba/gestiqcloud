from __future__ import annotations

import uuid

from sqlalchemy import JSON, Boolean, ForeignKey, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base

UUID = PGUUID(as_uuid=True)
TENANT_UUID = UUID.with_variant(String(36), "sqlite")


class TenantFieldConfig(Base):
    __tablename__ = "tenant_field_configs"

    id: Mapped[uuid.UUID] = mapped_column(TENANT_UUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        TENANT_UUID, ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    module: Mapped[str] = mapped_column(String, nullable=False, index=True)
    field: Mapped[str] = mapped_column(String, nullable=False)
    visible: Mapped[bool] = mapped_column(Boolean, default=True)
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    ord: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    label: Mapped[str | None] = mapped_column(Text, nullable=True)
    help: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Nuevas columnas para importación dinámica
    aliases: Mapped[dict | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=True,
        comment="Array de aliases: ['precio', 'pvp', 'price']",
    )
    field_type: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="'string', 'number', 'date', 'boolean'"
    )
    validation_pattern: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="Regex para validación"
    )
    validation_rules: Mapped[dict | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=True,
        comment="Reglas complejas: {min, max, custom}",
    )
    transform_expression: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="parseFloat(v.replace(...)) como string"
    )


class SectorFieldDefault(Base):
    __tablename__ = "sector_field_defaults"

    id: Mapped[uuid.UUID] = mapped_column(TENANT_UUID, primary_key=True, default=uuid.uuid4)
    sector: Mapped[str] = mapped_column(String, nullable=False, index=True)
    module: Mapped[str] = mapped_column(String, nullable=False, index=True)
    field: Mapped[str] = mapped_column(String, nullable=False)
    visible: Mapped[bool] = mapped_column(Boolean, default=True)
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    ord: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    label: Mapped[str | None] = mapped_column(Text, nullable=True)
    help: Mapped[str | None] = mapped_column(Text, nullable=True)
