from fastapi import  Request, HTTPException


def require_admin(request: Request):
    s = request.state.session or {}
    if s.get("kind") != "admin":
        raise HTTPException(401, "not authenticated as admin")
    return s

def require_tenant(request: Request): # pyright: ignore[reportUnknownParameterType]
    s = request.state.session or {} # type: ignore
    if s.get("kind") != "tenant": # type: ignore
        raise HTTPException(401, "not authenticated as tenant")
    return s # pyright: ignore[reportUnknownVariableType]

def set_tenant_scope(request: Request, tenant_id: str | None):
    if tenant_id:
        request.state.session["tenant_id"] = tenant_id
        request.state.session_dirty = True
