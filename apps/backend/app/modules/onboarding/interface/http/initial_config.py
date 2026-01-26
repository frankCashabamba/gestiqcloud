"""
@deprecated This module has been deprecated.

The initial configuration endpoint has been replaced by:
- Route: POST /api/v1/tenant/onboarding/init
- File: app/routers/onboarding_init.py

This legacy router is kept only for temporary compatibility.
TODO: Remove this file in the next version.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import get_current_user_context
from app.models.company.company_settings import CompanySettings

router = APIRouter()


class CompanySettingsCreate(BaseModel):
    """@deprecated - See onboarding_init.py"""

    default_language: str
    timezone: str
    currency: str
    company_logo: str | None = None
    primary_color: str = "#4f46e5"
    secondary_color: str = "#ffffff"


class CompanySettingsOut(BaseModel):
    """@deprecated - See onboarding_init.py"""

    company_name: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    company_logo: str | None = None


class AuthenticatedUser(BaseModel):
    """@deprecated - See onboarding_init.py"""

    tenant_id: UUID


def get_current_user() -> AuthenticatedUser:
    """@deprecated - See onboarding_init.py"""

    async def _get():
        user = await get_current_user_context()
        return AuthenticatedUser(tenant_id=user.get("tenant_id"))

    return _get


@router.post("/company-settings")
def save_company_settings(
    data: CompanySettingsCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    @deprecated
    Use POST /api/v1/tenant/onboarding/init instead.
    """
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
    """
    @deprecated
    Use GET /api/v1/company/settings instead.
    """
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
