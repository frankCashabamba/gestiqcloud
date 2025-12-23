"""Module: company_settings_router.py

Auto-generated module docstring."""

from app.config.database import get_db
from app.models import CompanySettings
from app.routers.protected import get_current_user
from app.schemas.company_settings import CompanySettingsCreate, CompanySettingsOut
from app.schemas.configuracion import AuthenticatedUser
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

router = APIRouter()


@router.post("/company-settings")
def save_company_settings(
    data: CompanySettingsCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    tenant_id = current_user.tenant_id

    existing = db.query(CompanySettings).filter_by(tenant_id=tenant_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Settings already exist for this company")

    new_settings = CompanySettings(
        tenant_id=tenant_id,
        default_language=data.default_language,
        timezone=data.timezone,
        currency=data.currency,
        company_logo=data.company_logo,
        primary_color=data.primary_color,
        secondary_color=data.secondary_color,
    )
    db.add(new_settings)
    db.commit()
    db.refresh(new_settings)
    return {"message": "Settings saved", "id": new_settings.id}


@router.get("/company-settings/{tenant_id}", response_model=CompanySettingsOut)
def get_company_settings(
    tenant_id: int,
    db: Session = Depends(get_db),
):
    settings = db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()

    if not settings:
        return {
            "company_name": None,
            "primary_color": None,
            "secondary_color": None,
            "company_logo": None,
        }

    return {
        "company_logo": settings.company_logo,
        "primary_color": settings.primary_color,
        "secondary_color": settings.secondary_color,
    }
