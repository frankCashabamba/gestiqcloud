"""Module: router_admins.py

Auto-generated module docstring."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.email.email_utils import reenviar_correo_reset
from app.config.database import get_db
from app.models.company.company_user import CompanyUser
from app.modules.users.infrastructure.schemas import CompanyUserOut

router = APIRouter()


@router.get("/api/company-admins", response_model=list[CompanyUserOut])
def list_company_admins(db: Session = Depends(get_db)):
    """List all company admins across tenants."""
    return db.query(CompanyUser).filter(CompanyUser.is_company_admin.is_(True)).all()


@router.post("/api/users/{user_id}/activate")
def activate_user(user_id: str, db: Session = Depends(get_db)):
    """Activate a company user."""
    usuario = db.query(CompanyUser).filter(CompanyUser.id == user_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="user_not_found")

    usuario.is_active = True
    db.commit()
    return {"msg": "user_activated"}


@router.post("/api/users/{user_id}/deactivate")
def deactivate_user(user_id: str, db: Session = Depends(get_db)):
    """Deactivate a company user."""
    usuario = db.query(CompanyUser).filter(CompanyUser.id == user_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="user_not_found")

    usuario.is_active = False
    db.commit()
    return {"msg": "user_deactivated"}


@router.post("/api/users/{user_id}/resend-reset")
def resend_reset(user_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Resend password reset email to a company user."""
    usuario = db.query(CompanyUser).filter(CompanyUser.id == user_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="user_not_found")

    reenviar_correo_reset(usuario.email, background_tasks)

    return {"msg": "reset_email_sent"}


@router.post("/api/companies/{tenant_id}/reassign-admin")
def reassign_admin(tenant_id: str, new_admin_id: str, db: Session = Depends(get_db)):
    """Assign a new company admin within the tenant."""
    usuarios = db.query(CompanyUser).filter(CompanyUser.tenant_id == tenant_id).all()

    if not usuarios:
        raise HTTPException(status_code=404, detail="no_users_for_company")

    for u in usuarios:
        u.is_company_admin = u.id == new_admin_id

    db.commit()
    return {"msg": "admin_reassigned"}
