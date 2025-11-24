# app/api/v1e/profile.py
from fastapi import APIRouter, Depends, Request

from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls

router = APIRouter(
    prefix="/me",
    tags=["Me"],
    dependencies=[Depends(with_access_claims), Depends(ensure_rls)],
)


@router.get("/tenant", dependencies=[Depends(require_scope("tenant"))])
def me_tenant(request: Request):
    c = request.state.access_claims
    return {
        "user_id": c.get("user_id"),
        "tenant_id": c.get("tenant_id"),
        "empresa_slug": c.get("empresa_slug"),
        "name": c.get("name"),
        "is_company_admin": c.get("is_company_admin"),
        "roles": c.get("roles", []),
        "permissions": c.get("permissions", {}),
        "plantilla": c.get("plantilla"),
    }


@router.get("/admin", dependencies=[Depends(require_scope("admin"))])
def me_admin(request: Request):
    c = request.state.access_claims
    return {
        "user_id": c.get("user_id"),
        "is_superadmin": c.get("is_superadmin", True),
        "user_type": c.get("user_type", "superadmin"),
    }
