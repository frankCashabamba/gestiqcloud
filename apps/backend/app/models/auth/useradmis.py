# app/models/security/useradmis.py
from datetime import datetime
from sqlalchemy import Boolean, Integer, String, DateTime, func, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.config.database import Base

class SuperUser(Base):
    """Tabla de usuarios (admin)."""
    __tablename__ = "auth_user"

    # PK (ya tienes un sequence en Postgres: auth_user_id_seq)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)

    # Identidad
    username: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True, nullable=False)

    # Credenciales
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Estado / permisos
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    is_superadmin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    is_staff: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    # Multi-tenant (ajusta a tu tipo real: UUID si tus tenants son UUID; si no, String)
    tenant_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), index=True, nullable=True)# pylint: ignore

    # Auditoría de acceso / seguridad
    failed_login_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_password_change_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()# pylint: disable=not-callable
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()# pylint: disable=not-callable
    )
