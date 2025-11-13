# app/models/security/auth_audit.py
from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4
from app.config.database import Base


class AuthAudit(Base):
    __tablename__ = "auth_audit"
    __table_args__ = {"extend_existing": True}
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    kind = Column(String, index=True)  # login|refresh|logout|reuse_detected
    scope = Column(String, index=True)  # admin|tenant
    user_id = Column(String, index=True, nullable=True)
    tenant_id = Column(String, index=True, nullable=True)
    ip = Column(String, nullable=True)
    ua = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
