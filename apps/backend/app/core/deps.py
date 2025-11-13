from typing import Any

from app.core.auth_shared import ensure_session
from fastapi import HTTPException, Request


def require_admin(request: Request) -> dict[str, Any]:
    s = getattr(request.state, "session", {}) or {}
    if s.get("kind") != "admin":
        raise HTTPException(status_code=401, detail="not authenticated as admin")
    return s


def require_tenant(request: Request) -> dict[str, Any]:
    s = getattr(request.state, "session", {}) or {}
    if s.get("kind") != "tenant":
        raise HTTPException(status_code=401, detail="not authenticated as tenant")
    return s


def set_tenant_scope(request: Request, tenant_id: str | None) -> None:
    if tenant_id:
        s = ensure_session(request)
        s["tenant_id"] = tenant_id
        request.state.session_dirty = True
