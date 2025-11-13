"""
Public Tenant Settings endpoints

GET /api/v1/settings/tenant-config -> composite config used by frontend TenantConfigContext
"""
from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.middleware.tenant import get_current_user
from app.models.core.settings import TenantSettings
from app.models.tenant import Tenant
from app.models.core.product_category import ProductCategory


router = APIRouter(prefix="/settings", tags=["Settings (public)"])


@router.get("/tenant-config", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
def get_tenant_config(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    tid = (
        UUID(current_user["tenant_id"]) if isinstance(current_user, dict) and current_user.get("tenant_id") else None
    )

    tenant = db.query(Tenant).filter(Tenant.id == tid).first() if tid else None
    settings_row = (
        db.query(TenantSettings).filter(TenantSettings.tenant_id == tid).first() if tid else None
    )

    # Defaults
    currency = settings_row.currency if settings_row else "EUR"
    locale = settings_row.locale if settings_row else "es"
    timezone = settings_row.timezone if settings_row else "Europe/Madrid"
    settings_obj: Dict[str, Any] = (settings_row.settings or {}) if settings_row else {}
    pos_config: Dict[str, Any] = (settings_row.pos_config or {}) if settings_row else {}

    # Categories (tenant-scoped)
    categories: List[Dict[str, Any]] = []
    if tid:
        cats = db.query(ProductCategory).filter(ProductCategory.tenant_id == tid).all()
        categories = [
            {"id": str(c.id), "name": c.name, "description": c.description}
            for c in cats
        ]

    # Enabled modules: derive from Tenant.config_json.enabled_modules if present
    enabled_modules: List[str] = []
    if tenant and isinstance(tenant.config_json, dict):
        mods = tenant.config_json.get("enabled_modules")
        if isinstance(mods, list):
            enabled_modules = [str(m) for m in mods]

    # Features: compute from settings/pos_config with safe defaults
    tax_conf = (pos_config.get("tax") if isinstance(pos_config, dict) else {}) or {}
    price_includes_tax = bool(tax_conf.get("price_includes_tax", True))
    default_tax_rate = (
        settings_obj.get("iva_tasa_defecto")
        or tax_conf.get("default_rate")
        or 0.15
    )
    try:
        default_tax_rate = float(default_tax_rate)
    except Exception:
        default_tax_rate = 0.15

    features = {
        # Inventario
        "inventory_expiry_tracking": bool(settings_obj.get("inventory_expiry_tracking", False)),
        "inventory_lot_tracking": bool(settings_obj.get("inventory_lot_tracking", False)),
        "inventory_serial_tracking": bool(settings_obj.get("inventory_serial_tracking", False)),
        "inventory_auto_reorder": bool(settings_obj.get("inventory_auto_reorder", False)),
        # POS
        "pos_enable_weights": bool(pos_config.get("enable_weights", False)) if isinstance(pos_config, dict) else False,
        "pos_enable_batch_tracking": bool(pos_config.get("enable_batch_tracking", False)) if isinstance(pos_config, dict) else False,
        "pos_receipt_width_mm": int(((pos_config.get("receipt") or {}).get("width_mm", 58)) if isinstance(pos_config, dict) else 58),
        "pos_return_window_days": int(pos_config.get("return_window_days", 15)) if isinstance(pos_config, dict) else 15,
        # General
        "price_includes_tax": price_includes_tax,
        "tax_rate": default_tax_rate,
    }

    # Sector flags
    plantilla = (tenant.sector_template_name if tenant and tenant.sector_template_name else "default").strip().lower()
    sector = {
        "plantilla": plantilla or "default",
        "is_panaderia": "panader" in (plantilla or ""),
        "is_taller": "taller" in (plantilla or ""),
        "is_retail": "retail" in (plantilla or ""),
    }

    data = {
        "tenant": {
            "id": str(tenant.id) if tenant else "",
            "name": tenant.name if tenant else "",
            "color_primario": (tenant.primary_color if tenant else "#4f46e5"),
            "plantilla_inicio": (tenant.default_template if tenant else "default"),
            "currency": (tenant.base_currency if tenant else currency),
            "country": (tenant.country_code if tenant else "ES"),
            "config_json": (tenant.config_json if tenant else {}),
        },
        "settings": {
            "settings": settings_obj,
            "pos_config": pos_config,
            "locale": locale,
            "timezone": timezone,
            "currency": currency,
        },
        "categories": categories,
        "enabled_modules": enabled_modules,
        "features": features,
        "sector": sector,
    }

    return data
