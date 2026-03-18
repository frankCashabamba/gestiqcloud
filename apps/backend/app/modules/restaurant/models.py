"""Restaurant module — Tables and orders (mesas y comandas)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.config.database import Base


class RestaurantTable(Base):
    __tablename__ = "restaurant_tables"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    number = Column(Integer, nullable=False)
    name = Column(String(50), nullable=True)  # "Mesa 1", "Terraza A", etc.
    capacity = Column(Integer, default=4)
    zone = Column(String(50), nullable=True)  # "Interior", "Terraza", "Barra"
    status = Column(String(20), default="available")  # available, occupied, reserved, cleaning
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    __table_args__ = (
        Index("uq_restaurant_table_number", "tenant_id", "number", unique=True),
    )


class RestaurantOrder(Base):
    __tablename__ = "restaurant_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    table_id = Column(UUID(as_uuid=True), ForeignKey("restaurant_tables.id"), nullable=False, index=True)
    order_number = Column(String(20), nullable=False)
    waiter_id = Column(UUID(as_uuid=True), nullable=True)
    waiter_name = Column(String(100), nullable=True)
    status = Column(String(20), default="open")  # open, preparing, served, paid, canceled
    guests = Column(Integer, default=1)
    notes = Column(Text, nullable=True)
    subtotal = Column(Numeric(12, 2), default=0)
    tax_total = Column(Numeric(12, 2), default=0)
    total = Column(Numeric(12, 2), default=0)
    opened_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    closed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    __table_args__ = (
        Index("ix_restaurant_orders_tenant_status", "tenant_id", "status"),
    )


class RestaurantOrderItem(Base):
    __tablename__ = "restaurant_order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("restaurant_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    product_name = Column(String(200), nullable=False)
    qty = Column(Numeric(10, 3), nullable=False, default=1)
    unit_price = Column(Numeric(12, 2), nullable=False)
    line_total = Column(Numeric(12, 2), nullable=False)
    notes = Column(Text, nullable=True)  # "Sin cebolla", "Extra queso"
    status = Column(String(20), default="pending")  # pending, preparing, ready, served, canceled
    sent_to_kitchen_at = Column(DateTime(timezone=True), nullable=True)
    ready_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
