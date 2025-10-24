"""
Compatibility tenant middleware/dependencies for legacy routers.

Provides ensure_tenant and get_current_user so older routers like
app.routers.pos and app.routers.payments can run against the modern
auth + RLS stack.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.db.rls import set_tenant_guc


def _resolve_tenant_uuid(claim_tid: str | None, db: Session) -> str:
    """
    Accepts tenant id from claims which may be an int empresa_id or
    a UUID string. Returns a UUID string. Raises if cannot resolve.
    """
    if not claim_tid:
        raise HTTPException(status_code=403, detail="missing_tenant")
    tid = str(claim_tid)
    if tid.isdigit():
        row = db.execute(text("SELECT id::text FROM tenants WHERE empresa_id=:eid"), {"eid": int(tid)}).first()
        if not row or not row[0]:
            raise HTTPException(status_code=403, detail="tenant_not_found")
        return str(row[0])
    return tid


def ensure_tenant(request: Request, db: Session = Depends(get_db)) -> str:
    """FastAPI dependency that ensures a valid tenant and sets the DB GUC.

    - Parses/validates the access token via with_access_claims
    - Resolves tenant UUID (supports legacy empresa_id in tokens)
    - Sets `app.tenant_id` (SET LOCAL) for RLS/trigger coherence
    - Returns the tenant UUID string
    """
    claims = with_access_claims(request)
    claim_tid = claims.get("tenant_id") if isinstance(claims, dict) else None
    tenant_uuid = _resolve_tenant_uuid(str(claim_tid) if claim_tid is not None else None, db)
    try:
        set_tenant_guc(db, tenant_uuid, persist=False)
    except Exception:
        # Non-fatal: proceed without aborting request
        pass
    # Also expose on request for downstream use
    try:
        request.state.tenant_id = tenant_uuid
    except Exception:
        pass
    return tenant_uuid


def get_current_user(request: Request) -> dict:
    """Returns a minimal user dict from access claims for legacy routers.

    Expected keys: id (user_id in token), roles(optional)
    """
    claims = getattr(request.state, "access_claims", None)
    if not isinstance(claims, dict):
        claims = with_access_claims(request)
    uid = claims.get("user_id") if isinstance(claims, dict) else None
    if uid is None:
        raise HTTPException(status_code=401, detail="missing_user")
    return {"id": uid, "roles": claims.get("roles", []) if isinstance(claims, dict) else []}

