# app/core/audit.py
from app.models.security.auth_audit import AuthAudit
from sqlalchemy.orm import Session
from fastapi import Request

def audit(db: Session, *, kind: str, scope: str, user_id: str|None, tenant_id: str|None, req: Request):
    db.add(AuthAudit(
        kind=kind,
        scope=scope,
        user_id=user_id,
        tenant_id=tenant_id,
        ip=(req.client.host if req.client else None),
        ua=req.headers.get("user-agent"),
    ))
    db.commit()
