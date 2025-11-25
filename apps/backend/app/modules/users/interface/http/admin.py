from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.core.security import get_password_hash
from app.models.company.company_user import CompanyUser

router = APIRouter(
    prefix="/users",  # mounted under /api/v1/admin via build_api_router
    tags=["admin:users"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("admin"))],
)


class SetPasswordIn(BaseModel):
    password: str = Field(min_length=8)


@router.post("/{user_id}/set-password")
def set_password(user_id: UUID, payload: SetPasswordIn, db: Session = Depends(get_db)):
    """Set password for a tenant admin user (CompanyUser).

    Requires admin scope. Does not return the password or hash.
    """
    user = db.query(CompanyUser).filter(CompanyUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="user_not_found")
    # Only tenant admins; never superusers or other user types
    if not bool(getattr(user, "is_company_admin", False)):
        raise HTTPException(status_code=403, detail="not_tenant_admin")
    if len(payload.password or "") < 8:
        raise HTTPException(status_code=400, detail="weak_password")

    user.password_hash = get_password_hash(payload.password)
    db.add(user)
    db.commit()
    return {"ok": True}
