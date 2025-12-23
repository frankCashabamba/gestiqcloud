"""
DEPRECATED - Tenant Configuration Router

⚠️ Este archivo está deprecado. Las funciones se movieron a:
   app/routers/tenant_settings.py

Mantiene backward compatibility redirectando a tenant_settings.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.middleware.tenant import ensure_tenant
from app.routers.tenant_settings import get_tenant_settings_compat, update_tenant_settings_compat

router = APIRouter(prefix="/api/v1/settings", tags=["settings [DEPRECATED]"])


@router.get("/tenant", deprecated=True)
def get_tenant_settings(db: Session = Depends(get_db), tenant_id: str = Depends(ensure_tenant)):
    """
    ⚠️ DEPRECATED - Usar GET /api/v1/tenants/{tenant_id}/settings

    Obtener configuración del tenant (moneda, IVA, POS, etc.)
    """
    return get_tenant_settings_compat(db, tenant_id)


@router.put("/tenant", deprecated=True)
def update_tenant_settings(
    settings: dict,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
):
    """
    ⚠️ DEPRECATED - Usar PUT /api/v1/tenants/{tenant_id}/settings

    Actualizar configuración del tenant
    """
    from app.routers.tenant_settings import TenantSettingsRequest

    # Convert dict to Pydantic model
    payload = TenantSettingsRequest(
        locale=settings.get("locale"),
        timezone=settings.get("timezone"),
        currency=settings.get("currency"),
        settings=settings.get("settings"),
    )

    return update_tenant_settings_compat(payload, db, tenant_id)
