"""Product variants — Size, Color, and custom attributes."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.config.database import Base


class ProductAttribute(Base):
    __tablename__ = "product_attributes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(50), nullable=False)  # "Talla", "Color", "Medida"
    values = Column(JSONB, default=list)  # ["S", "M", "L", "XL"] or ["Rojo", "Azul"]
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    __table_args__ = (Index("uq_product_attr_tenant_name", "tenant_id", "name", unique=True),)


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sku = Column(String(50), nullable=True)
    attributes = Column(JSONB, nullable=False, default=dict)  # {"Talla": "M", "Color": "Rojo"}
    price_override = Column(Numeric(12, 2), nullable=True)
    cost_override = Column(Numeric(12, 2), nullable=True)
    barcode = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index(
            "uq_product_variant_sku",
            "tenant_id",
            "sku",
            unique=True,
            postgresql_where="sku IS NOT NULL",
        ),
        Index("ix_product_variants_product", "tenant_id", "product_id"),
    )
