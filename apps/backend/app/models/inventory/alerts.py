"""
Inventory Alerts Models
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from sqlalchemy import Column, String, Boolean, Integer, Float, Text, DateTime, ARRAY, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class AlertConfig(Base):
    """Configuration for inventory alerts"""
    __tablename__ = "inventory_alert_configs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=UUID)
    tenant_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    alert_type = Column(String(50), nullable=False, default="low_stock")
    threshold_type = Column(String(20), nullable=False, default="fixed")  # fixed, percentage
    threshold_value = Column(Float, nullable=True)

    # Filters
    warehouse_ids = Column(ARRAY(PGUUID(as_uuid=True)), default=list)
    category_ids = Column(ARRAY(PGUUID(as_uuid=True)), default=list)
    product_ids = Column(ARRAY(PGUUID(as_uuid=True)), default=list)

    # Notification channels
    notify_email = Column(Boolean, default=False)
    email_recipients = Column(ARRAY(String), default=list)
    notify_whatsapp = Column(Boolean, default=False)
    whatsapp_numbers = Column(ARRAY(String), default=list)
    notify_telegram = Column(Boolean, default=False)
    telegram_chat_ids = Column(ARRAY(String), default=list)

    # Schedule
    check_frequency_minutes = Column(Integer, default=60)
    last_checked_at = Column(DateTime, nullable=True)
    next_check_at = Column(DateTime, nullable=True, index=True)

    # Settings
    cooldown_hours = Column(Integer, default=24)
    max_alerts_per_day = Column(Integer, default=10)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    history = relationship("AlertHistory", back_populates="config", cascade="all, delete-orphan")


class AlertHistory(Base):
    """History of sent alerts"""
    __tablename__ = "inventory_alert_history"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=UUID)
    tenant_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    alert_config_id = Column(PGUUID(as_uuid=True), ForeignKey("inventory_alert_configs.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    warehouse_id = Column(PGUUID(as_uuid=True), nullable=True, index=True)
    alert_type = Column(String(50), nullable=False)
    threshold_value = Column(Float, nullable=True)
    current_stock = Column(Float, nullable=True)
    message = Column(Text, nullable=True)
    channels_sent = Column(ARRAY(String), default=list)
    sent_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    config = relationship("AlertConfig", back_populates="history")
