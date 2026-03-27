from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.core.audit_event import AuditEvent


def normalize_audit_changes(value: Any) -> Any:
    """Return a JSON-safe representation for audit payloads."""
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (bytes, bytearray)):
        return value.hex()
    if isinstance(value, dict):
        return {str(key): normalize_audit_changes(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [normalize_audit_changes(item) for item in value]
    if hasattr(value, "id"):
        raw_id = getattr(value, "id", None)
        if raw_id is not None:
            return str(raw_id)
    return str(value)


def audit_event(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: str | None,
    actor_type: str,
    source: str,
    tenant_id: str | None,
    user_id: str | None,
    changes: dict[str, Any] | None = None,
    req: Request | None = None,
) -> None:
    """Best-effort audit: never break request flow if DB model/tables are missing."""
    try:
        ip = req.client.host if req and req.client else None
        ua = req.headers.get("user-agent") if req else None
        db.add(
            AuditEvent(
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                actor_type=actor_type,
                source=source,
                tenant_id=tenant_id,
                user_id=user_id,
                changes=normalize_audit_changes(changes) if changes else None,
                ip=ip,
                ua=ua,
            )
        )
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
