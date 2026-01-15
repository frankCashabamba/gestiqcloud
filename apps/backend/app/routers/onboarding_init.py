"""Onboarding initialization endpoint.

Guarda la configuración inicial del tenant tanto en Tenant como en CompanySettings.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import get_current_user_context
from app.models.tenant import Tenant
from app.models.company.company_settings import CompanySettings

router = APIRouter(prefix="/tenant/onboarding", tags=["Onboarding"])


class OnboardingInitRequest(BaseModel):
    """Solicitud de inicialización del onboarding."""
    
    # Información de empresa (Tenant)
    company_name: str
    tax_id: Optional[str] = None
    country_code: str
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    website: Optional[str] = None
    
    # Configuración (CompanySettings)
    default_language: str
    timezone: str
    currency: str
    logo_empresa: Optional[str] = None
    primary_color: str = "#4f46e5"
    secondary_color: str = "#ffffff"


@router.post("/init")
async def onboarding_init(
    payload: OnboardingInitRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_context),
):
    """
    Inicializa la configuración del tenant.
    
    Guarda información de empresa en Tenant y configuración operativa en CompanySettings.
    Requiere token JWT válido con tenant_id en los claims.
    """
    tenant_id: UUID = current_user.get("tenant_id")
    
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Missing tenant_id in token")
    
    try:
        # 1. Actualizar Tenant con información de empresa
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        tenant.name = payload.company_name
        tenant.country_code = payload.country_code
        tenant.tax_id = payload.tax_id
        tenant.phone = payload.phone
        tenant.address = payload.address
        tenant.city = payload.city
        tenant.state = payload.state
        tenant.postal_code = payload.postal_code
        tenant.website = payload.website
        tenant.base_currency = payload.currency
        
        # 2. Crear o actualizar CompanySettings con configuración operativa
        settings = db.query(CompanySettings).filter(
            CompanySettings.tenant_id == tenant_id
        ).first()
        
        if settings:
            # Actualizar existentes
            settings.default_language = payload.default_language
            settings.timezone = payload.timezone
            settings.currency = payload.currency
            settings.company_logo = payload.logo_empresa
            settings.primary_color = payload.primary_color
            settings.secondary_color = payload.secondary_color
        else:
            # Crear nuevos settings
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
        
        # Guardar cambios
        db.add(tenant)
        db.commit()
        
        return {
            "ok": True,
            "message": "Onboarding configuration saved successfully",
            "tenant_id": str(tenant_id),
        }
        
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error saving onboarding: {str(e)}")
