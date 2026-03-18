"""MFA — TOTP (Time-based One-Time Password) + Recovery Codes."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import struct
import time
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID

from app.config.database import Base


class UserMFA(Base):
    __tablename__ = "user_mfa"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("company_users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    totp_secret = Column(String(64), nullable=False)
    is_enabled = Column(Boolean, default=False)
    recovery_codes = Column(ARRAY(String), default=list)  # hashed codes
    backup_email = Column(String(255), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


def generate_totp_secret() -> str:
    return secrets.token_hex(20)


def generate_recovery_codes(count: int = 8) -> tuple[list[str], list[str]]:
    """Returns (plain_codes, hashed_codes)."""
    plain = [f"{secrets.randbelow(10**8):08d}" for _ in range(count)]
    hashed = [hashlib.sha256(c.encode()).hexdigest() for c in plain]
    return plain, hashed


def _dynamic_truncate(hmac_digest: bytes) -> int:
    offset = hmac_digest[-1] & 0x0F
    code = struct.unpack(">I", hmac_digest[offset : offset + 4])[0]
    return (code & 0x7FFFFFFF) % 10**6


def verify_totp(secret: str, code: str, window: int = 1) -> bool:
    """Verify a TOTP code with a time window."""
    if len(code) != 6 or not code.isdigit():
        return False
    key = bytes.fromhex(secret)
    now = int(time.time()) // 30
    for offset in range(-window, window + 1):
        counter = struct.pack(">Q", now + offset)
        h = hmac.new(key, counter, hashlib.sha1).digest()
        if f"{_dynamic_truncate(h):06d}" == code:
            return True
    return False


def get_totp_uri(secret: str, email: str, issuer: str = "GestiqCloud") -> str:
    """Generate otpauth:// URI for QR code."""
    import base64

    b32_secret = base64.b32encode(bytes.fromhex(secret)).decode().rstrip("=")
    return f"otpauth://totp/{issuer}:{email}?secret={b32_secret}&issuer={issuer}&digits=6&period=30"
