from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope

router = APIRouter(
    prefix="/admin/companies",
    tags=["Admin Companies"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("admin"))],
)


class DeleteAllCompaniesIn(BaseModel):
    confirm: str


def _request_with_delete_confirmation(request: Request, tenant_id: str) -> Request:
    """
    Clone current request scope and inject per-tenant destructive delete confirmation header.
    """
    scope = dict(request.scope)
    headers = list(scope.get("headers", []))
    headers = [(k, v) for (k, v) in headers if k.lower() != b"x-confirm-delete-tenant"]
    headers.append((b"x-confirm-delete-tenant", str(tenant_id).encode("utf-8")))
    scope["headers"] = headers
    return Request(scope, request.receive)


@router.post("/purge-orphans")
def purge_orphans(db: Session = Depends(get_db)) -> dict:
    """Remove orphaned rows left from previous deletes."""
    assigned_modules = (
        db.execute(
            text("DELETE FROM assigned_modules WHERE tenant_id NOT IN (SELECT id FROM tenants)")
        ).rowcount
        or 0
    )
    company_user_roles = (
        db.execute(
            text("DELETE FROM company_user_roles WHERE tenant_id NOT IN (SELECT id FROM tenants)")
        ).rowcount
        or 0
    )
    company_roles = (
        db.execute(
            text("DELETE FROM company_roles WHERE tenant_id NOT IN (SELECT id FROM tenants)")
        ).rowcount
        or 0
    )
    company_modules = (
        db.execute(
            text("DELETE FROM company_modules WHERE tenant_id NOT IN (SELECT id FROM tenants)")
        ).rowcount
        or 0
    )
    user_profiles = (
        db.execute(
            text("DELETE FROM user_profiles WHERE tenant_id NOT IN (SELECT id FROM tenants)")
        ).rowcount
        or 0
    )
    company_users = (
        db.execute(
            text("DELETE FROM company_users WHERE tenant_id NOT IN (SELECT id FROM tenants)")
        ).rowcount
        or 0
    )
    db.commit()
    return {
        "ok": True,
        "deleted": {
            "assigned_modules": assigned_modules,
            "company_user_roles": company_user_roles,
            "company_roles": company_roles,
            "company_modules": company_modules,
            "user_profiles": user_profiles,
            "company_users": company_users,
        },
    }


@router.post("/bulk/delete-all")
def delete_all_companies(
    payload: DeleteAllCompaniesIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(with_access_claims),
) -> dict:
    """
    Delete all tenants using the same logic as single-company DELETE endpoint.

    Safety:
    - Requires payload.confirm == "DELETE_ALL_COMPANIES"
    - Each deletion reuses the existing delete_company() behavior and guards.
    """
    if (payload.confirm or "").strip() != "DELETE_ALL_COMPANIES":
        raise HTTPException(status_code=400, detail="invalid_bulk_delete_confirmation")

    rows = db.execute(text("SELECT id, name FROM tenants ORDER BY created_at DESC")).all()
    deleted: list[dict] = []
    failed: list[dict] = []

    if not rows:
        return {"ok": True, "total": 0, "deleted": [], "failed": []}

    # Import inside function to avoid module-level circular import side effects.
    from app.modules.company.interface.http.admin import delete_company

    for tenant_id, tenant_name in rows:
        tid = str(tenant_id)
        try:
            req_with_confirm = _request_with_delete_confirmation(request, tid)
            result = delete_company(
                tenant_id=tid,
                request=req_with_confirm,
                db=db,
                current_user=current_user,
            )
            deleted.append(
                {
                    "tenant_id": tid,
                    "name": tenant_name,
                    "result": result,
                }
            )
        except HTTPException as e:
            try:
                db.rollback()
            except Exception:
                pass
            failed.append(
                {
                    "tenant_id": tid,
                    "name": tenant_name,
                    "status_code": e.status_code,
                    "detail": e.detail,
                }
            )
        except Exception as e:
            try:
                db.rollback()
            except Exception:
                pass
            failed.append(
                {
                    "tenant_id": tid,
                    "name": tenant_name,
                    "status_code": 500,
                    "detail": str(e),
                }
            )

    return {
        "ok": len(failed) == 0,
        "total": len(rows),
        "deleted_count": len(deleted),
        "failed_count": len(failed),
        "deleted": deleted,
        "failed": failed,
    }
