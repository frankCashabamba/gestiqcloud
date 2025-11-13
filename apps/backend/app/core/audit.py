# app/core/audit.py
from app.models.security.auth_audit import AuthAudit
from fastapi import Request
from sqlalchemy.orm import Session


def audit(
    db: Session,
    *,
    kind: str,
    scope: str,
    user_id: str | None,
    tenant_id: str | None,
    req: Request,
):
    """Best-effort audit: never break request flow if DB model/tables are missing in tests."""
    try:
        db.add(
            AuthAudit(
                kind=kind,
                scope=scope,
                user_id=user_id,
                tenant_id=tenant_id,
                ip=(req.client.host if req.client else None),
                ua=req.headers.get("user-agent"),
            )
        )
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        # swallow errors in audit during tests or when table isn't present
        return
