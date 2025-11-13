# app/models/security/useradmis.py
from datetime import datetime
import uuid
from sqlalchemy import Boolean, Integer, String, DateTime, func, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from app.config.database import Base, IS_SQLITE


class SuperUser(Base):
    """Tabla de usuarios (admin)."""

    __tablename__ = "auth_user"
    __table_args__ = {"extend_existing": True}

    # PK UUID
    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()") if not IS_SQLITE else None,
        index=True,
    )

    # Identidad
    username: Mapped[str] = mapped_column(
        String(150), unique=True, index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(
        String(254), unique=True, index=True, nullable=False
    )

    # Credenciales
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Estado / permisos
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    is_superadmin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    is_staff: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )

    # Nota: SuperUser es global (no por tenant); no incluir tenant_id

    # Auditoría de acceso / seguridad
    failed_login_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_password_change_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),  # pylint: disable=not-callable
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),  # pylint: disable=not-callable
    )
