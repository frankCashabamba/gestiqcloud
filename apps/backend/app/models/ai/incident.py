import uuid
from datetime import datetime

from app.config.database import Base
from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")

# UUID type that works with both PostgreSQL and SQLite
PG_UUID = UUID().with_variant(String(36), "sqlite")


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        Index("idx_incidents_tenant_estado", "tenant_id", "estado"),
        Index("idx_incidents_created_at", "created_at"),
        Index("idx_incidents_severidad", "severidad"),
        {"extend_existing": True},
    )

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(PG_UUID, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    tipo = Column(String(50), nullable=False)  # error, warning, bug, feature_request, stock_alert
    severidad = Column(String(20), nullable=False)  # low, medium, high, critical
    titulo = Column(String(255), nullable=False)
    descripcion = Column(Text)
    stack_trace = Column(Text)
    context = Column(JSON_TYPE)
    estado = Column(
        String(20), default="open", nullable=False
    )  # open, in_progress, resolved, closed
    # Fix FK to company users table
    assigned_to = Column(
        PG_UUID,
        ForeignKey("usuarios_usuarioempresa.id", ondelete="SET NULL"),
    )
    auto_detected = Column(Boolean, default=False)
    auto_resolved = Column(Boolean, default=False)
    ia_analysis = Column(JSON_TYPE)
    ia_suggestion = Column(Text)
    resolved_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="incidents")
    assigned_user = relationship("UsuarioEmpresa", foreign_keys=[assigned_to])


class StockAlert(Base):
    __tablename__ = "stock_alerts"
    __table_args__ = (
        Index("idx_stock_alerts_tenant_status", "tenant_id", "status"),
        Index("idx_stock_alerts_product", "product_id"),
        {"extend_existing": True},
    )

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(PG_UUID, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(
        PG_UUID,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    warehouse_id = Column(PG_UUID, ForeignKey("warehouses.id", ondelete="SET NULL"))
    alert_type = Column(
        String(50), nullable=False
    )  # low_stock, out_of_stock, expiring, expired, overstock
    threshold_config = Column(JSON_TYPE)
    current_qty = Column(Integer)
    threshold_qty = Column(Integer)
    status = Column(String(20), default="active", nullable=False)  # active, acknowledged, resolved
    incident_id = Column(PG_UUID, ForeignKey("incidents.id", ondelete="SET NULL"))
    ia_recommendation = Column(Text)
    notified_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant")
    product = relationship("Product")
    # warehouse = relationship("Warehouse")  # TODO: Crear modelo Warehouse
    incident = relationship("Incident")


class NotificationChannel(Base):
    __tablename__ = "notification_channels"
    __table_args__ = (
        Index("idx_notification_channels_tenant", "tenant_id"),
        {"extend_existing": True},
    )

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(PG_UUID, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    tipo = Column(String(50), nullable=False)  # email, whatsapp, telegram, slack
    name = Column(String(100), nullable=False)
    config = Column(JSON_TYPE, nullable=False)  # {api_key, phone, chat_id, webhook_url, etc}
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant = relationship("Tenant")
    notification_logs = relationship("NotificationLog", back_populates="channel")


class NotificationLog(Base):
    __tablename__ = "notification_log"
    __table_args__ = (
        Index("idx_notification_log_tenant", "tenant_id"),
        Index("idx_notification_log_status", "status"),
        Index("idx_notification_log_sent_at", "sent_at"),
        {"extend_existing": True},
    )

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(PG_UUID, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    channel_id = Column(PG_UUID, ForeignKey("notification_channels.id", ondelete="SET NULL"))
    incident_id = Column(PG_UUID, ForeignKey("incidents.id", ondelete="CASCADE"))
    stock_alert_id = Column(PG_UUID, ForeignKey("stock_alerts.id", ondelete="CASCADE"))
    tipo = Column(String(50), nullable=False)
    recipient = Column(String(255), nullable=False)
    subject = Column(String(255))
    body = Column(Text)
    status = Column(String(20), default="pending", nullable=False)  # pending, sent, failed
    error_message = Column(Text)
    extra_data = Column(JSON_TYPE)  # Renamed from metadata (reserved word)
    sent_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant")
    channel = relationship("NotificationChannel", back_populates="notification_logs")
    incident = relationship("Incident")
    stock_alert = relationship("StockAlert")
