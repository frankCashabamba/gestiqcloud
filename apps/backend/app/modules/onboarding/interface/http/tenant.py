"""Onboarding initialization endpoint.

Saves the initial tenant configuration in both Tenant and CompanySettings.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import get_current_user_context
from app.models.company.company_settings import CompanySettings
from app.models.tenant import Tenant

router = APIRouter(prefix="/tenant/onboarding", tags=["Onboarding"])


class OnboardingInitRequest(BaseModel):
    """Onboarding initialization request."""

    # Company information (Tenant)
    company_name: str
    tax_id: str | None = None
    country_code: str
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    website: str | None = None

    # Configuration (CompanySettings)
    default_language: str
    timezone: str
    currency: str
    logo_empresa: str | None = None
    primary_color: str = "#4f46e5"
    secondary_color: str = "#ffffff"


@router.post("/init")
async def onboarding_init(
    payload: OnboardingInitRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_context),
):
    """
    Initialize the tenant configuration.

    Saves company information in Tenant and operational configuration in CompanySettings.
    Requires a valid JWT token with tenant_id in the claims.
    """
    tenant_id: UUID = current_user.get("tenant_id")

    if not tenant_id:
        raise HTTPException(status_code=401, detail="Missing tenant_id in token")

    try:
        # 1. Update Tenant with company information
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()

        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        tenant.name = payload.company_name
        # Actualizar slug si es genérico ("default", vacío) para reflejar el nombre real
        if not tenant.slug or tenant.slug in ("default", "tenant", "empresa"):
            import re
            import unicodedata
            def _slugify(text: str) -> str:
                text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
                text = re.sub(r"[^\w\s-]", "", text.lower()).strip()
                text = re.sub(r"[\s_-]+", "-", text)
                return text[:60] or "empresa"
            new_slug = _slugify(payload.company_name)
            # Verificar unicidad; si ya existe agregar sufijo numérico
            from sqlalchemy import func as _func
            existing = db.query(Tenant).filter(Tenant.slug == new_slug, Tenant.id != tenant_id).first()
            if existing:
                count = db.query(_func.count(Tenant.id)).filter(
                    Tenant.slug.like(f"{new_slug}%"), Tenant.id != tenant_id
                ).scalar() or 0
                new_slug = f"{new_slug}-{count + 1}"
            tenant.slug = new_slug
        tenant.country_code = payload.country_code
        tenant.tax_id = payload.tax_id
        tenant.phone = payload.phone
        tenant.address = payload.address
        tenant.city = payload.city
        tenant.state = payload.state
        tenant.postal_code = payload.postal_code
        tenant.website = payload.website
        tenant.base_currency = payload.currency

        # 2. Create or update CompanySettings with operational configuration
        settings = db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()

        if settings:
            # Update existing settings
            settings.default_language = payload.default_language
            settings.timezone = payload.timezone
            settings.currency = payload.currency
            settings.company_logo = payload.logo_empresa
            settings.primary_color = payload.primary_color
            settings.secondary_color = payload.secondary_color
            settings.company_name = payload.company_name
            settings.tax_id = payload.tax_id
        else:
            # Create new settings
            settings = CompanySettings(
                tenant_id=tenant_id,
                default_language=payload.default_language,
                timezone=payload.timezone,
                currency=payload.currency,
                company_logo=payload.logo_empresa,
                primary_color=payload.primary_color,
                secondary_color=payload.secondary_color,
                company_name=payload.company_name,
                tax_id=payload.tax_id,
            )
            db.add(settings)

        # Marcar onboarding como completado en settings JSON
        # flag_modified es necesario para que SQLAlchemy detecte mutaciones en JSONB
        from sqlalchemy.orm.attributes import flag_modified
        settings.settings = {**(settings.settings or {}), "onboarding_complete": True}
        flag_modified(settings, "settings")

        # Save changes
        db.add(tenant)
        db.add(settings)
        db.commit()

        return {
            "ok": True,
            "message": "Onboarding configuration saved successfully",
            "tenant_id": str(tenant_id),
            "empresa_slug": getattr(tenant, "slug", None),
        }

    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error saving onboarding: {str(e)}")
