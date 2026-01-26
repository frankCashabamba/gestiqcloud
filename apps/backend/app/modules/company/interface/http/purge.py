from __future__ import annotations

from fastapi import APIRouter, Depends
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


@router.post("/purge-orphans")
def purge_orphans(db: Session = Depends(get_db)) -> dict:
    """Remove orphaned rows left from previous deletes."""
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
    return {"ok": True, "deleted": {"user_profiles": user_profiles, "company_users": company_users}}
