"""Admin user management endpoints."""
from __future__ import annotations

from uuid import UUID

from app.api.email.email_utils import reenviar_correo_reset
from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.models.company.company_user import CompanyUser as CompanyUser
from app.models.tenant import Tenant as Company
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="",
    dependencies=[Depends(with_access_claims), Depends(require_scope("admin"))],
)


@router.get("")
def list_users(db: Session = Depends(get_db)):
    """List main users (company admins)."""
    rows = (
        db.query(CompanyUser)
        .join(Company, Company.id == CompanyUser.tenant_id)
        .filter(CompanyUser.is_company_admin.is_(True))
        .order_by(CompanyUser.id.desc())
        .limit(500)
        .all()
    )

    def to_item(u: CompanyUser):
        full_name = " ".join(
            [
                getattr(u, "first_name", "") or "",
                getattr(u, "last_name", "") or "",
            ]
        ).strip()
        return {
            "id": str(getattr(u, "id", None)) if hasattr(u, "id") else None,
            "name": full_name or None,
            "email": getattr(u, "email", None),
            "is_company_admin": bool(getattr(u, "is_company_admin", False)),
            "active": bool(getattr(u, "is_active", True)),
        }

    return [to_item(u) for u in rows]


@router.post("/{user_id}/resend-reset")
def resend_reset(
    user_id: UUID, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    """Resend password reset email.

    In development, if EMAIL_DEV_LOG_ONLY=true (or SMTP is missing), the reset link is printed to logs.
    """
    user = db.query(CompanyUser).filter(CompanyUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not getattr(user, "email", None):
        raise HTTPException(status_code=400, detail="User without email")

    reenviar_correo_reset(user.email, background_tasks)
    return {"msg": "ok"}


@router.post("/{user_id}/activate")
def activate_user(user_id: UUID, db: Session = Depends(get_db)):
    """Activate a user."""
    u = db.query(CompanyUser).filter(CompanyUser.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    if not bool(getattr(u, "is_company_admin", False)):
        raise HTTPException(status_code=403, detail="not_tenant_admin")
    u.active = True
    db.add(u)
    db.commit()
    return {"ok": True}


@router.post("/{user_id}/deactivate")
def deactivate_user(user_id: UUID, db: Session = Depends(get_db)):
    """Deactivate a user."""
    u = db.query(CompanyUser).filter(CompanyUser.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    if not bool(getattr(u, "is_company_admin", False)):
        raise HTTPException(status_code=403, detail="not_tenant_admin")
    u.active = False
    db.add(u)
    db.commit()
    return {"ok": True}


@router.post("/{user_id}/deactivate-company")
def deactivate_company(user_id: UUID, db: Session = Depends(get_db)):
    """Deactivate the company associated with a user."""
    u = db.query(CompanyUser).filter(CompanyUser.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    company = db.query(Company).filter(Company.id == u.tenant_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    company.active = False
    db.add(company)
    db.commit()
    return {"ok": True}
