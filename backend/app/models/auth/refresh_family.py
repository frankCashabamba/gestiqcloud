# app/models/auth/refresh_family.py
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import DateTime, String, Index, Integer, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class RefreshFamily(Base):
    __tablename__ = "auth_refresh_family"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Si auth_user.id es INTEGER (como tu SuperUser), usa Integer aquí o quítale la FK.
    user_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    # Si tus tenants son UUID, mantenlo UUID (si no, cambia al tipo real)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="family",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

class RefreshToken(Base):
    __tablename__ = "auth_refresh_token"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_refresh_family.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # identificadores de token en UUID (evita colisiones y es consistente)
    jti: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, index=True, default=uuid.uuid4)
    prev_jti: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)

    ua_hash: Mapped[str | None] = mapped_column(Text)   # hashes largos → Text
    ip_hash: Mapped[str | None] = mapped_column(Text)

    token: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    family: Mapped["RefreshFamily"] = relationship(back_populates="tokens")

# Índices útiles (igual que tenías):
Index("ix_auth_refresh_token_expires_at", RefreshToken.expires_at)
Index("ix_auth_refresh_family_revoked_at", RefreshFamily.revoked_at)
