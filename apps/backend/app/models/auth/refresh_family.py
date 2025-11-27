# app/models/auth/refresh_family.py
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import String as SQLString
from sqlalchemy.types import TypeDecorator

from app.db.base import Base


class GUID(TypeDecorator):
    """Platform-independent GUID type."""

    impl = SQLString(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            return str(uuid.UUID(value))
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)


class RefreshFamily(Base):
    __tablename__ = "auth_refresh_family"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(GUID, index=True, nullable=True)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(GUID, index=True, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tokens: Mapped[list[RefreshToken]] = relationship(
        back_populates="family",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class RefreshToken(Base):
    __tablename__ = "auth_refresh_token"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)

    family_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("auth_refresh_family.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    jti: Mapped[uuid.UUID] = mapped_column(GUID, unique=True, index=True, default=uuid.uuid4)
    prev_jti: Mapped[uuid.UUID | None] = mapped_column(GUID, index=True)

    ua_hash: Mapped[str | None] = mapped_column(Text)
    ip_hash: Mapped[str | None] = mapped_column(Text)

    token: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    family: Mapped[RefreshFamily] = relationship(back_populates="tokens")


Index("ix_auth_refresh_token_expires_at", RefreshToken.expires_at)
Index("ix_auth_refresh_family_revoked_at", RefreshFamily.revoked_at)
