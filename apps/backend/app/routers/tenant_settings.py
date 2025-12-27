"""
Tenant Settings Router - Configuración centralizada por tenant

Consolidación completada en CompanySettings:
- Eliminado modelo duplicado TenantSettings
- Usamos CompanySettings para toda la configuración

URLs:
- GET  /api/v1/tenants/{tenant_id}/settings  - Obtener configuración
- PUT  /api/v1/tenants/{tenant_id}/settings  - Actualizar configuración
- GET  /api/v1/settings/tenant (backward compat) - Obtener (middleware)
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.authz import require_scope
from app.core.access_guard import with_access_claims
from app.db.rls import set_tenant_guc
from app.middleware.tenant import ensure_tenant
from app.models.company.company_settings import CompanySettings
from app.models.company.company import SectorTemplate
from app.models.tenant import Tenant
from app.services.sector_templates import apply_sector_template
from app.schemas.sector_plantilla import SectorConfigJSON

router = APIRouter(prefix="/api/v1/company", tags=["Company Settings"])
router_compat = APIRouter(
    prefix="/api/v1",
    tags=["Company Settings (compat)"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("admin"))],
)


class TenantSettingsRequest(BaseModel):
    """Request model para actualizar tenant settings"""

    locale: str | None = None
    timezone: str | None = None
    currency: str | None = None
    sector_id: int | str | None = None
    sector_template_name: str | None = None
    sector_plantilla_nombre: str | None = None  # alias usado por Admin UI
    sector_plantilla_id: int | None = None
    # Configuración modular (se almacena en JSONB settings / columnas dedicadas)
    inventory: dict | None = None
    pos_config: dict | None = None
    invoice_config: dict | None = None
    settings: dict | None = None


class TenantSettingsResponse(BaseModel):
    """Response model para tenant settings"""

    ok: bool = True
    locale: str | None = None
    timezone: str | None = None
    currency: str | None = None
    sector_id: int | str | None = None
    sector_template_name: str | None = None
    sector_plantilla_name: str | None = None  # Backward compat
    inventory: dict | None = None
    pos_config: dict | None = None
    invoice_config: dict | None = None
    settings: dict



@router.get("/settings", summary="Obtener configuración de la empresa")
def get_tenant_settings(tenant_id: str = Depends(ensure_tenant), db: Session = Depends(get_db)):
    """
    Obtiene la configuración del tenant (idioma, zona horaria, moneda, etc.)

    Args:
        tenant_id: UUID del tenant

    Returns:
        Configuración completa del tenant
    """
    # Validar que el tenant existe
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    # Obtener CompanySettings si existe (sin crear defaults implícitos)
    company_settings = (
        db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    )
    if not company_settings:
        return TenantSettingsResponse(
            locale=None,
            timezone=None,
            currency=None,
            sector_id=getattr(tenant, "sector_id", None)
            if isinstance(getattr(tenant, "sector_id", None), int)
            else getattr(tenant, "sector_template_name", None),
            sector_template_name=getattr(tenant, "sector_template_name", None),
            sector_plantilla_name=getattr(tenant, "sector_template_name", None),
            inventory=None,
            pos_config=None,
            invoice_config=None,
            settings={},
        )

    # Desempaquetar configuraciones modulares para compatibilidad con frontends
    settings_json = company_settings.settings or {}
    inventory_cfg = settings_json.get("inventory") if isinstance(settings_json, dict) else None

    return TenantSettingsResponse(
        locale=company_settings.default_language,
        timezone=company_settings.timezone,
        currency=company_settings.currency,
        sector_id=getattr(tenant, "sector_id", None) if isinstance(getattr(tenant, "sector_id", None), int) else getattr(tenant, "sector_template_name", None),
        sector_template_name=getattr(tenant, "sector_template_name", None),
        sector_plantilla_name=getattr(tenant, "sector_template_name", None),  # Backward compat
        inventory=inventory_cfg,
        pos_config=company_settings.pos_config,
        invoice_config=company_settings.invoice_config,
        settings=settings_json,
    )


@router.put("/settings", summary="Actualizar configuración de la empresa")
def update_tenant_settings(
    payload: TenantSettingsRequest,
    tenant_id: str = Depends(ensure_tenant),
    db: Session = Depends(get_db),
):
    """
    Actualiza la configuración del tenant.

    Soporta:
    - Idioma, zona horaria, moneda
    - Sector y plantilla de sector
    - Configuración general (JSONB)
    - Aplicar plantilla de sector automáticamente

    Args:
        tenant_id: UUID del tenant
        payload: Configuración a actualizar

    Returns:
        Configuración actualizada
    """
    # Validar que el tenant existe
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    # Obtener o crear CompanySettings
    company_settings = db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    if not company_settings:
        if not payload.locale:
            raise HTTPException(status_code=400, detail="default_language_required")
        if not payload.timezone:
            raise HTTPException(status_code=400, detail="timezone_required")
        if not payload.currency:
            raise HTTPException(status_code=400, detail="currency_required")
        primary_color = getattr(tenant, "primary_color", None)
        secondary_color = None
        template_name = getattr(tenant, "sector_template_name", None)
        if template_name:
            template = (
                db.query(SectorTemplate)
                .filter((SectorTemplate.code == template_name) | (SectorTemplate.name == template_name))
                .first()
            )
            if template:
                config = SectorConfigJSON(**(template.template_config or {}))
                primary_color = config.branding.color_primario
                secondary_color = config.branding.color_secundario
        if not primary_color:
            raise HTTPException(status_code=400, detail="primary_color_required")
        if not secondary_color:
            raise HTTPException(status_code=400, detail="secondary_color_required")
        company_settings = CompanySettings(
            tenant_id=tenant_id,
            default_language=payload.locale,
            timezone=payload.timezone,
            currency=payload.currency,
            primary_color=primary_color,
            secondary_color=secondary_color,
        )
        db.add(company_settings)
        db.flush()

    # Actualizar campos escalares (mapear locale -> default_language)
    if payload.locale is not None:
        company_settings.default_language = payload.locale
    if payload.timezone is not None:
        company_settings.timezone = payload.timezone
    if payload.currency is not None:
        company_settings.currency = payload.currency

    # Configuración modular: mergea en JSONB o columnas dedicadas
    if payload.inventory is not None:
        current_settings = company_settings.settings or {}
        if not isinstance(current_settings, dict):
            current_settings = {}
        current_settings["inventory"] = payload.inventory
        company_settings.settings = current_settings

    if payload.pos_config is not None:
        company_settings.pos_config = payload.pos_config

    if payload.invoice_config is not None:
        company_settings.invoice_config = payload.invoice_config

    # Actualizar sector en el tenant
    if payload.sector_id is not None:
        try:
            tenant.sector_id = int(payload.sector_id)
        except (ValueError, TypeError):
            # Modern sector templates usan UUID; guardamos en nombre y limpiamos sector_id numérico
            tenant.sector_id = None
            if payload.sector_template_name is None and payload.sector_plantilla_nombre is None:
                tenant.sector_template_name = str(payload.sector_id)

    # Actualizar sector_template_name en el tenant (acepta alias sector_plantilla_nombre)
    template_name = payload.sector_template_name or payload.sector_plantilla_nombre
    if template_name is not None:
        tenant.sector_template_name = template_name

    # Mergear settings generales en JSONB
    if payload.settings:
        current_settings = company_settings.settings or {}
        if not isinstance(current_settings, dict):
            current_settings = {}
        current_settings.update(payload.settings)
        company_settings.settings = current_settings

    # Aplicar plantilla de sector si se proporciona
    if payload.sector_plantilla_id:
        try:
            apply_sector_template(
                db,
                tenant_id,
                int(payload.sector_plantilla_id),
                override_existing=True,
                design_only=True,
            )
        except Exception as e:
            # Log pero no falla el endpoint completo
            raise HTTPException(
                status_code=400,
                detail=f"Error aplicando plantilla de sector: {str(e)}",
            )

    # Guardar cambios
    db.commit()
    db.refresh(company_settings)

    sector_template = getattr(tenant, "sector_template_name", None)
    sector_id_raw = getattr(tenant, "sector_id", None)
    sector_id_value = sector_id_raw if isinstance(sector_id_raw, int) else sector_template

    return TenantSettingsResponse(
        ok=True,
        locale=company_settings.default_language,
        timezone=company_settings.timezone,
        currency=company_settings.currency,
        sector_id=sector_id_value,
        sector_template_name=sector_template,
        sector_plantilla_name=sector_template,
        inventory=(company_settings.settings or {}).get("inventory") if isinstance(company_settings.settings, dict) else None,
        pos_config=company_settings.pos_config,
        invoice_config=company_settings.invoice_config,
        settings=company_settings.settings or {},
    )


# ============================================================
# SECTIONED ENDPOINTS - Frontend expects these
# ============================================================


@router.get("/settings/general", summary="Obtener configuración general")
def get_settings_general(tenant_id: str = Depends(ensure_tenant), db: Session = Depends(get_db)):
    """Get general settings (idioma, zona horaria, moneda)"""
    settings = get_tenant_settings(tenant_id, db)
    return {
        "default_language": settings.locale,
        "timezone": settings.timezone,
        "currency": settings.currency,
    }


@router.put("/settings/general", summary="Actualizar configuración general")
def update_settings_general(
    payload: dict,
    tenant_id: str = Depends(ensure_tenant),
    db: Session = Depends(get_db),
):
    """Update general settings"""
    request = TenantSettingsRequest(
        locale=payload.get("default_language"),
        timezone=payload.get("timezone"),
        currency=payload.get("currency"),
    )
    return update_tenant_settings(request, tenant_id, db)


@router.get("/settings/branding", summary="Obtener configuración de branding")
def get_settings_branding(tenant_id: str = Depends(ensure_tenant), db: Session = Depends(get_db)):
    """Get branding settings (colores, logo)"""
    company_settings = (
        db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    )
    if not company_settings:
        return {"primary_color": None, "secondary_color": None, "company_logo": None}

    return {
        "primary_color": company_settings.primary_color,
        "secondary_color": company_settings.secondary_color,
        "company_logo": company_settings.company_logo,
    }


@router.put("/settings/branding", summary="Actualizar configuración de branding")
def update_settings_branding(
    payload: dict,
    tenant_id: str = Depends(ensure_tenant),
    db: Session = Depends(get_db),
):
    """Update branding settings"""
    company_settings = (
        db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    )
    if not company_settings:
        raise HTTPException(status_code=404, detail="Settings not found")

    if "primary_color" in payload:
        company_settings.primary_color = payload["primary_color"]
    if "secondary_color" in payload:
        company_settings.secondary_color = payload["secondary_color"]
    if "company_logo" in payload:
        company_settings.company_logo = payload["company_logo"]

    db.commit()
    db.refresh(company_settings)

    return {
        "primary_color": company_settings.primary_color,
        "secondary_color": company_settings.secondary_color,
        "company_logo": company_settings.company_logo,
    }


@router.get("/settings/fiscal", summary="Obtener configuración fiscal")
def get_settings_fiscal(tenant_id: str = Depends(ensure_tenant), db: Session = Depends(get_db)):
    """Get fiscal settings (tax_id, tax_regime)"""
    company_settings = (
        db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    )
    if not company_settings:
        return {}

    return {
        "tax_id": company_settings.tax_id,
        "tax_regime": company_settings.tax_regime,
        "company_name": company_settings.company_name,
    }


@router.put("/settings/fiscal", summary="Actualizar configuración fiscal")
def update_settings_fiscal(
    payload: dict,
    tenant_id: str = Depends(ensure_tenant),
    db: Session = Depends(get_db),
):
    """Update fiscal settings"""
    company_settings = (
        db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    )
    if not company_settings:
        raise HTTPException(status_code=404, detail="Settings not found")

    if "tax_id" in payload:
        company_settings.tax_id = payload["tax_id"]
    if "tax_regime" in payload:
        company_settings.tax_regime = payload["tax_regime"]
    if "company_name" in payload:
        company_settings.company_name = payload["company_name"]

    db.commit()
    db.refresh(company_settings)

    return {
        "tax_id": company_settings.tax_id,
        "tax_regime": company_settings.tax_regime,
        "company_name": company_settings.company_name,
    }


@router.get("/settings/horarios", summary="Obtener configuración de horarios")
def get_settings_horarios(tenant_id: str = Depends(ensure_tenant), db: Session = Depends(get_db)):
    """Get horarios settings (working_days, business_hours)"""
    company_settings = (
        db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    )
    if not company_settings:
        return {"working_days": [], "business_hours": {}}

    return {
        "working_days": company_settings.working_days or [],
        "business_hours": company_settings.business_hours or {},
    }


@router.put("/settings/horarios", summary="Actualizar configuración de horarios")
def update_settings_horarios(
    payload: dict,
    tenant_id: str = Depends(ensure_tenant),
    db: Session = Depends(get_db),
):
    """Update horarios settings"""
    company_settings = (
        db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    )
    if not company_settings:
        raise HTTPException(status_code=404, detail="Settings not found")

    if "working_days" in payload:
        company_settings.working_days = payload["working_days"]
    if "business_hours" in payload:
        company_settings.business_hours = payload["business_hours"]

    db.commit()
    db.refresh(company_settings)

    return {
        "working_days": company_settings.working_days or [],
        "business_hours": company_settings.business_hours or {},
    }


@router.get("/settings/limites", summary="Obtener configuración de límites")
def get_settings_limites(tenant_id: str = Depends(ensure_tenant), db: Session = Depends(get_db)):
    """Get limites settings (user_limit, custom_roles)"""
    company_settings = (
        db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    )
    if not company_settings:
        return {"user_limit": 10, "allow_custom_roles": True}

    return {
        "user_limit": company_settings.user_limit,
        "allow_custom_roles": company_settings.allow_custom_roles,
    }


@router.put("/settings/limites", summary="Actualizar configuración de límites")
def update_settings_limites(
    payload: dict,
    tenant_id: str = Depends(ensure_tenant),
    db: Session = Depends(get_db),
):
    """Update limites settings"""
    company_settings = (
        db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    )
    if not company_settings:
        raise HTTPException(status_code=404, detail="Settings not found")

    if "user_limit" in payload:
        company_settings.user_limit = payload["user_limit"]
    if "allow_custom_roles" in payload:
        company_settings.allow_custom_roles = payload["allow_custom_roles"]

    db.commit()
    db.refresh(company_settings)

    return {
        "user_limit": company_settings.user_limit,
        "allow_custom_roles": company_settings.allow_custom_roles,
    }


# ============================================================
# BACKWARD COMPATIBILITY - MIDDLEWARE-BASED ENDPOINTS
# ============================================================
# Mantienen rutas antiguas para no romper clientes existentes


@router.get("/settings/tenant", summary="[DEPRECATED] Obtener settings del tenant")
def get_tenant_settings_compat(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
):
    """
    DEPRECATED: Usar GET /api/v1/tenants/{tenant_id}/settings

    Mantiene backward compatibility con código legacy que usa middleware.
    """
    return get_tenant_settings(tenant_id, db)


@router.put("/settings/tenant", summary="[DEPRECATED] Actualizar settings del tenant")
def update_tenant_settings_compat(
    payload: TenantSettingsRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
):
    """
    DEPRECATED: Usar PUT /api/v1/tenants/{tenant_id}/settings

    Mantiene backward compatibility con código legacy que usa middleware.
    """
    return update_tenant_settings(payload, tenant_id, db)


# ============================================================
# COMPATIBILITY ROUTES (admin panel expects these direct paths)
# ============================================================


def _set_rls(db: Session, tenant_id: str) -> None:
    try:
        set_tenant_guc(db, tenant_id, persist=False)
    except Exception:
        pass


@router_compat.get("/tenants/{tenant_id}/settings", summary="Obtener settings por tenant_id (compat)")
def get_tenant_settings_admin(
    tenant_id: str,
    db: Session = Depends(get_db),
):
    _set_rls(db, tenant_id)
    return get_tenant_settings(tenant_id, db)


@router_compat.put("/tenants/{tenant_id}/settings", summary="Actualizar settings por tenant_id (compat)")
def update_tenant_settings_admin(
    tenant_id: str,
    payload: TenantSettingsRequest,
    db: Session = Depends(get_db),
):
    _set_rls(db, tenant_id)
    return update_tenant_settings(payload, tenant_id, db)


@router_compat.put("/admin/empresas/{tenant_id}/settings", summary="Actualizar settings legacy admin")
def update_tenant_settings_admin_legacy(
    tenant_id: str,
    payload: TenantSettingsRequest,
    db: Session = Depends(get_db),
):
    _set_rls(db, tenant_id)
    return update_tenant_settings(payload, tenant_id, db)
