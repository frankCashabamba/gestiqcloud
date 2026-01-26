"""Company Settings Router - Centralized configuration per company.

URLs:
- GET  /api/v1/company/settings
- PUT  /api/v1/company/settings
"""

import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from uuid import UUID
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.authz import require_scope
from app.core.access_guard import with_access_claims
from app.core.audit_events import audit_event
from app.db.rls import set_tenant_guc
from app.middleware.tenant import ensure_tenant
from app.models.company.company_settings import CompanySettings
from app.models.company.company import SectorTemplate
from app.models.tenant import Tenant
from app.models.core.country_catalogs import CountryIdType
from app.services.sector_templates import apply_sector_template
from app.schemas.sector_plantilla import SectorConfigJSON

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/company", tags=["Company Settings"])
router_admin = APIRouter(
    prefix="/admin/companies",
    tags=["Company Settings (admin)"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("admin"))],
)


class CompanySettingsRequest(BaseModel):
    """Request model to update company settings"""

    locale: str | None = None
    timezone: str | None = None
    currency: str | None = None
    sector_id: int | str | None = None
    sector_template_name: str | None = None
    sector_plantilla_nombre: str | None = None  # alias used by Admin UI
    sector_plantilla_id: int | None = None
    # Modular configuration (stored in JSONB settings / dedicated columns)
    inventory: dict | None = None
    pos_config: dict | None = None
    invoice_config: dict | None = None
    settings: dict | None = None


class CompanySettingsResponse(BaseModel):
    """Response model for company settings"""

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



@router.get("/settings", summary="Get company settings")
def get_company_settings(tenant_id: str = Depends(ensure_tenant), db: Session = Depends(get_db)):
    """
    Gets the tenant configuration (language, timezone, currency, etc.)

    Args:
        tenant_id: UUID of the tenant

    Returns:
        Complete tenant configuration
    """
    # Validate that the tenant exists
    try:
        tenant_key = UUID(str(tenant_id))
    except Exception:
        tenant_key = tenant_id
    tenant = db.query(Tenant).filter(Tenant.id == tenant_key).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Get CompanySettings if exists (without creating implicit defaults)
    company_settings = (
        db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_key).first()
    )
    if not company_settings:
        return CompanySettingsResponse(
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

    # Unpack modular configurations for frontend compatibility
    settings_json = company_settings.settings or {}
    if isinstance(settings_json, dict):
        settings_copy = dict(settings_json)
    else:
        settings_copy = {}

    try:
        documents_cfg = settings_copy.get("documents") if isinstance(settings_copy, dict) else None
        if not isinstance(documents_cfg, dict):
            documents_cfg = {}
        country_code = (
            documents_cfg.get("country")
            or getattr(tenant, "country_code", None)
            or settings_copy.get("pais")
        )
        if country_code:
            rows = (
                db.query(CountryIdType)
                .filter(
                    CountryIdType.country_code == country_code,
                    CountryIdType.active.is_(True),
                )
                .order_by(CountryIdType.code.asc())
                .all()
            )
            documents_cfg["id_types"] = [r.code for r in rows]
            settings_copy["documents"] = documents_cfg
    except Exception:
        pass
    inventory_cfg = settings_json.get("inventory") if isinstance(settings_json, dict) else None

    return CompanySettingsResponse(
        locale=company_settings.default_language,
        timezone=company_settings.timezone,
        currency=company_settings.currency,
        sector_id=getattr(tenant, "sector_id", None) if isinstance(getattr(tenant, "sector_id", None), int) else getattr(tenant, "sector_template_name", None),
        sector_template_name=getattr(tenant, "sector_template_name", None),
        sector_plantilla_name=getattr(tenant, "sector_template_name", None),  # Backward compat
        inventory=inventory_cfg,
        pos_config=company_settings.pos_config,
        invoice_config=company_settings.invoice_config,
        settings=settings_copy,
    )


@router.put("/settings", summary="Update company settings")
def update_company_settings(
    payload: CompanySettingsRequest,
    request: Request,
    tenant_id: str = Depends(ensure_tenant),
    db: Session = Depends(get_db),
):
    """
    Updates the tenant configuration.

    Supports:
    - Language, timezone, currency
    - Sector and sector template
    - General configuration (JSONB)
    - Apply sector template automatically

    Args:
        tenant_id: UUID of the tenant
        payload: Configuration to update

    Returns:
        Updated configuration
    """
    # Debug logging (safe on Windows cp1252 consoles)
    try:
        raw = payload.model_dump() if hasattr(payload, "model_dump") else payload  # type: ignore[attr-defined]
        logger.debug(
            "company_settings.update payload=%s",
            json.dumps(raw, ensure_ascii=True, default=str),
        )
    except Exception:
        logger.debug("company_settings.update payload=<unprintable>")

    # Validate that the tenant exists
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Get or create CompanySettings
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

    # Update scalar fields (map locale -> default_language)
    update_fields: list[str] = []
    if payload.locale is not None:
        company_settings.default_language = payload.locale
        update_fields.append("locale")
    if payload.timezone is not None:
        company_settings.timezone = payload.timezone
        update_fields.append("timezone")
    if payload.currency is not None:
        company_settings.currency = payload.currency
        update_fields.append("currency")

    try:
        inv_from_settings = (
            (payload.settings or {}).get("inventory") if isinstance(payload.settings, dict) else None
        )
        logger.debug(
            "company_settings.update inventory=%s settings.inventory=%s",
            json.dumps(payload.inventory, ensure_ascii=True, default=str),
            json.dumps(inv_from_settings, ensure_ascii=True, default=str),
        )
    except Exception:
        logger.debug("company_settings.update inventory=<unprintable>")

    # Modular configuration: merge in JSONB or dedicated columns
    from sqlalchemy.orm.attributes import flag_modified

    inventory_payload = payload.inventory
    if inventory_payload is None and isinstance(payload.settings, dict):
        inventory_payload = payload.settings.get("inventory")
    current_settings = company_settings.settings or {}
    if not isinstance(current_settings, dict):
        current_settings = {}
    if inventory_payload is not None:
        current_settings["inventory"] = inventory_payload
        update_fields.append("inventory")

    if payload.pos_config is not None:
        company_settings.pos_config = payload.pos_config
        update_fields.append("pos_config")

    if payload.invoice_config is not None:
        company_settings.invoice_config = payload.invoice_config
        update_fields.append("invoice_config")

    # Update sector in the tenant
    if payload.sector_id is not None:
        try:
            tenant.sector_id = int(payload.sector_id)
        except (ValueError, TypeError):
            # Modern sector templates use UUID; save in name and clear numeric sector_id
            tenant.sector_id = None
            if payload.sector_template_name is None and payload.sector_plantilla_nombre is None:
                tenant.sector_template_name = str(payload.sector_id)
        update_fields.append("sector_id")

    # Update sector_template_name in the tenant (accepts alias sector_plantilla_nombre)
    template_name = payload.sector_template_name or payload.sector_plantilla_nombre
    if template_name is not None:
        tenant.sector_template_name = template_name
        update_fields.append("sector_template_name")

    # Merge general settings in JSONB
    if payload.settings:
        settings_payload = payload.settings
        if isinstance(settings_payload, dict) and "inventory" in settings_payload:
            settings_payload = {k: v for k, v in settings_payload.items() if k != "inventory"}
        current_settings.update(settings_payload)
        update_fields.append("settings")

    if payload.settings or inventory_payload is not None:
        company_settings.settings = dict(current_settings)
        flag_modified(company_settings, "settings")

    # Apply sector template if provided
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
            # Log but don't fail the entire endpoint
            raise HTTPException(
                status_code=400,
                detail=f"Error applying sector template: {str(e)}",
            )
        update_fields.append("sector_plantilla_id")

    # Save changes
    db.commit()
    db.refresh(company_settings)

    try:
        claims = getattr(getattr(request, "state", None), "access_claims", None) if request else None
        user_id = claims.get("user_id") if isinstance(claims, dict) else None
        audit_event(
            db,
            action="update",
            entity_type="company_settings",
            entity_id=str(tenant_id),
            actor_type="user" if user_id else "system",
            source="api",
            tenant_id=str(tenant_id),
            user_id=str(user_id) if user_id else None,
            changes={"fields": sorted(set(update_fields))} if update_fields else None,
            req=request,
        )
    except Exception:
        pass

    sector_template = getattr(tenant, "sector_template_name", None)
    sector_id_raw = getattr(tenant, "sector_id", None)
    sector_id_value = sector_id_raw if isinstance(sector_id_raw, int) else sector_template

    return CompanySettingsResponse(
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


@router.get("/settings/general", summary="Get general settings")
def get_settings_general(tenant_id: str = Depends(ensure_tenant), db: Session = Depends(get_db)):
    """Get general settings (language, timezone, currency, basic data)"""
    settings = get_company_settings(tenant_id, db)
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    company_settings = (
        db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    )
    return {
        "default_language": settings.locale,
        "timezone": settings.timezone,
        "currency": settings.currency,
        "company_name": (company_settings.company_name if company_settings else None)
        or (tenant.name if tenant else None),
        "tax_id": (company_settings.tax_id if company_settings else None)
        or (tenant.tax_id if tenant else None),
        "address": tenant.address if tenant else None,
        "country_code": tenant.country_code if tenant else None,
        "phone": tenant.phone if tenant else None,
        "city": tenant.city if tenant else None,
        "state": tenant.state if tenant else None,
        "postal_code": tenant.postal_code if tenant else None,
        "website": tenant.website if tenant else None,
    }


@router.put("/settings/general", summary="Update general settings")
def update_settings_general(
    payload: dict,
    request: Request,
    tenant_id: str = Depends(ensure_tenant),
    db: Session = Depends(get_db),
):
    """Update general settings"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    company_settings = (
        db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    )
    company_name = payload.get("company_name") or payload.get("razon_social") or payload.get("name")
    tax_id = payload.get("tax_id") or payload.get("ruc")
    address = payload.get("address") or payload.get("direccion")
    country_code = payload.get("country_code")
    phone = payload.get("phone")
    city = payload.get("city")
    state = payload.get("state")
    postal_code = payload.get("postal_code")
    website = payload.get("website")
    if tenant:
        if company_name is not None:
            tenant.name = company_name
        if tax_id is not None:
            tenant.tax_id = tax_id
        if address is not None:
            tenant.address = address
        if country_code is not None:
            tenant.country_code = country_code
        if phone is not None:
            tenant.phone = phone
        if city is not None:
            tenant.city = city
        if state is not None:
            tenant.state = state
        if postal_code is not None:
            tenant.postal_code = postal_code
        if website is not None:
            tenant.website = website
    if company_settings:
        if company_name is not None:
            company_settings.company_name = company_name
        if tax_id is not None:
            company_settings.tax_id = tax_id
    payload_model = CompanySettingsRequest(
        locale=payload.get("default_language"),
        timezone=payload.get("timezone"),
        currency=payload.get("currency"),
    )
    if (
        payload_model.locale is None
        and payload_model.timezone is None
        and payload_model.currency is None
    ):
        db.commit()
        return get_settings_general(tenant_id, db)
    result = update_company_settings(
        request=request,
        payload=payload_model,
        tenant_id=tenant_id,
        db=db,
    )
    return result


@router.get("/settings/branding", summary="Get branding settings")
def get_settings_branding(tenant_id: str = Depends(ensure_tenant), db: Session = Depends(get_db)):
    """Get branding settings (colors, logo)"""
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


@router.put("/settings/branding", summary="Update branding settings")
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


@router.get("/settings/fiscal", summary="Get fiscal settings")
def get_settings_fiscal(tenant_id: str = Depends(ensure_tenant), db: Session = Depends(get_db)):
    """Get fiscal settings (tax_id, tax_regime, iva)"""
    company_settings = (
        db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    )
    if not company_settings:
        return {}

    settings_json = company_settings.settings or {}
    iva_rate = None
    if isinstance(settings_json, dict):
        iva_rate = settings_json.get("iva_tasa_defecto")
    iva_percent = None
    if isinstance(iva_rate, (int, float)):
        iva_percent = iva_rate * 100 if iva_rate <= 1 else iva_rate

    return {
        "tax_id": company_settings.tax_id,
        "tax_regime": company_settings.tax_regime,
        "company_name": company_settings.company_name,
        "iva": iva_percent,
    }


@router.put("/settings/fiscal", summary="Update fiscal settings")
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
    if "tax_regime" in payload or "regimen" in payload:
        company_settings.tax_regime = payload.get("tax_regime") or payload.get("regimen")
    if "company_name" in payload:
        company_settings.company_name = payload["company_name"]
    if "iva" in payload:
        iva_raw = payload.get("iva")
        try:
            iva_num = float(iva_raw) if iva_raw is not None else None
        except (TypeError, ValueError):
            iva_num = None
        if iva_num is not None:
            iva_rate = iva_num / 100 if iva_num > 1 else iva_num
            settings_json = company_settings.settings or {}
            if not isinstance(settings_json, dict):
                settings_json = {}
            settings_json["iva_tasa_defecto"] = iva_rate
            company_settings.settings = settings_json

    db.commit()
    db.refresh(company_settings)

    settings_json = company_settings.settings or {}
    iva_rate = None
    if isinstance(settings_json, dict):
        iva_rate = settings_json.get("iva_tasa_defecto")
    iva_percent = None
    if isinstance(iva_rate, (int, float)):
        iva_percent = iva_rate * 100 if iva_rate <= 1 else iva_rate

    return {
        "tax_id": company_settings.tax_id,
        "tax_regime": company_settings.tax_regime,
        "company_name": company_settings.company_name,
        "iva": iva_percent,
    }


@router.get("/settings/horarios", summary="Get schedule settings")
def get_settings_horarios(tenant_id: str = Depends(ensure_tenant), db: Session = Depends(get_db)):
    """Get schedule settings (working_days, business_hours)"""
    company_settings = (
        db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    )
    if not company_settings:
        return {"working_days": [], "business_hours": {}}

    return {
        "working_days": company_settings.working_days or [],
        "business_hours": company_settings.business_hours or {},
    }


@router.put("/settings/horarios", summary="Update schedule settings")
def update_settings_horarios(
    payload: dict,
    tenant_id: str = Depends(ensure_tenant),
    db: Session = Depends(get_db),
):
    """Update schedule settings"""
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


@router.get("/settings/limits", summary="Get limits settings")
@router.get("/settings/limites", summary="Get limits settings (legacy)")
def get_settings_limites(tenant_id: str = Depends(ensure_tenant), db: Session = Depends(get_db)):
    """Get limits settings (user_limit, custom_roles)"""
    company_settings = (
        db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    )
    if not company_settings:
        return {"user_limit": 10, "allow_custom_roles": True}

    return {
        "user_limit": company_settings.user_limit,
        "allow_custom_roles": company_settings.allow_custom_roles,
    }


@router.put("/settings/limits", summary="Update limits settings")
@router.put("/settings/limites", summary="Update limits settings (legacy)")
def update_settings_limites(
    payload: dict,
    tenant_id: str = Depends(ensure_tenant),
    db: Session = Depends(get_db),
):
    """Update limits settings"""
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


@router_admin.get("/{tenant_id}/company/settings/limits", summary="Get limits settings by company_id")
@router_admin.get("/{tenant_id}/company/settings/limites", summary="Get limits settings by company_id (legacy)")
def get_settings_limites_admin(tenant_id: str, db: Session = Depends(get_db)):
    _set_rls(db, tenant_id)
    company_settings = (
        db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    )
    if not company_settings:
        return {"user_limit": 10, "allow_custom_roles": True}

    return {
        "user_limit": company_settings.user_limit,
        "allow_custom_roles": company_settings.allow_custom_roles,
    }


@router_admin.put("/{tenant_id}/company/settings/limits", summary="Update limits settings by company_id")
@router_admin.put("/{tenant_id}/company/settings/limites", summary="Update limits settings by company_id (legacy)")
def update_settings_limites_admin(
    tenant_id: str,
    payload: dict,
    db: Session = Depends(get_db),
):
    _set_rls(db, tenant_id)
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
# ADMIN ROUTES - CROSS-TENANT COMPANY SETTINGS
# ============================================================


def _set_rls(db: Session, tenant_id: str) -> None:
    try:
        set_tenant_guc(db, tenant_id, persist=False)
    except Exception:
        pass


@router_admin.get("/{tenant_id}/company/settings", summary="Get company settings by company_id")
def get_company_settings_admin(
    tenant_id: str,
    db: Session = Depends(get_db),
):
    _set_rls(db, tenant_id)
    return get_company_settings(tenant_id, db)


@router_admin.put("/{tenant_id}/company/settings", summary="Update company settings by company_id")
def update_company_settings_admin(
    tenant_id: str,
    payload: CompanySettingsRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    _set_rls(db, tenant_id)
    return update_company_settings(
        request=request,
        payload=payload,
        tenant_id=tenant_id,
        db=db,
    )
