from __future__ import annotations

from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.core.audit_event import AuditEvent


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
                changes=changes or None,
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
