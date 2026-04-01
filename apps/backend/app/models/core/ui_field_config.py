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
    # Nuevas columnas para importacion dinamica
    aliases: Mapped[dict | None] = mapped_column(
        JSONB(none_as_null=True).with_variant(JSON(none_as_null=True), "sqlite"),
        nullable=True,
        comment="Array de aliases: ['precio', 'pvp', 'price']",
    )
    field_type: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="'string', 'number', 'date', 'boolean'"
    )
    validation_pattern: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="Regex para validacion"
    )
    validation_rules: Mapped[dict | None] = mapped_column(
        JSONB(none_as_null=True).with_variant(JSON(none_as_null=True), "sqlite"),
        nullable=True,
        comment="Reglas complejas: {min, max, custom}",
    )
    transform_expression: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="parseFloat(v.replace(...)) como string"
    )
    options: Mapped[dict | None] = mapped_column(
        JSONB(none_as_null=True).with_variant(JSON(none_as_null=True), "sqlite"),
        nullable=True,
        comment="Array de opciones para select: ['Opcion 1', 'Opcion 2']",
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
    field_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    options: Mapped[dict | None] = mapped_column(
        JSONB(none_as_null=True).with_variant(JSON(none_as_null=True), "sqlite"),
        nullable=True,
        comment="Array de opciones para select: ['Opcion 1', 'Opcion 2']",
    )
    validation_pattern: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="Regex para validacion"
    )


class UiFieldConfigScopeRule(Base):
    __tablename__ = "ui_field_config_scope_rules"

    id: Mapped[uuid.UUID] = mapped_column(TENANT_UUID, primary_key=True, default=uuid.uuid4)
    scope_type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True, comment="sector_exact | module_prefix"
    )
    scope_value: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(16), nullable=False, default="deny")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
