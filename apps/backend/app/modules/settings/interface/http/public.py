"""
Public Company Settings endpoints

GET /api/v1/company/settings/config -> composite config used by frontend TenantConfigContext
"""

import re
import unicodedata
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.middleware.tenant import get_current_user
from app.models.company.company import SectorTemplate
from app.models.company.company_settings import CompanySettings
from app.models.core.module import CompanyModule, Module
from app.models.core.product_category import ProductCategory
from app.models.tenant import Tenant

router = APIRouter(prefix="/company/settings", tags=["Company Settings (public)"])


def _normalize_slug(value: str) -> str:
    value = (value or "").strip().lower()
    value = unicodedata.normalize("NFD", value)
    value = "".join(c for c in value if unicodedata.category(c) != "Mn")
    value = re.sub(r"\s+", "", value)
    return value


def _module_slug(module: Module) -> str:
    if getattr(module, "url", None):
        raw = str(module.url or "").lstrip("/")
        slug = raw.split("/")[0] if raw else ""
        if slug:
            return _normalize_slug(slug)
    return _normalize_slug(getattr(module, "name", "") or "")


@router.get("/config", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
def get_tenant_config(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    tid = (
        UUID(current_user["tenant_id"])
        if isinstance(current_user, dict) and current_user.get("tenant_id")
        else None
    )

    tenant = db.query(Tenant).filter(Tenant.id == tid).first() if tid else None
    settings_row = (
        db.query(CompanySettings).filter(CompanySettings.tenant_id == tid).first() if tid else None
    )

    settings_obj: dict[str, Any] = (settings_row.settings or {}) if settings_row else {}
    pos_config: dict[str, Any] = (settings_row.pos_config or {}) if settings_row else {}
    template_config: dict[str, Any] = {}
    template_defaults: dict[str, Any] = {}
    template_pos: dict[str, Any] = {}
    template_inventory: dict[str, Any] = {}

    plantilla = _normalize_slug(
        tenant.sector_template_name if tenant and tenant.sector_template_name else "default"
    )

    sector_template = None
    sector_features = {}
    if plantilla and plantilla != "default":
        sector_template = db.query(SectorTemplate).filter(SectorTemplate.code == plantilla).first()
        if sector_template:
            template_config = sector_template.template_config or {}
            template_defaults = template_config.get("defaults", {}) or {}
            template_pos = template_config.get("pos", {}) or {}
            template_inventory = template_config.get("inventory", {}) or {}
            sector_features = template_config.get("features", {})

    currency = (
        settings_row.currency
        if settings_row and settings_row.currency
        else (tenant.base_currency if tenant else None)
    )
    locale = (
        settings_row.default_language if settings_row and settings_row.default_language else None
    )
    timezone = settings_row.timezone if settings_row and settings_row.timezone else None
    price_includes_tax_default = (
        template_defaults.get("price_includes_tax") if isinstance(template_defaults, dict) else None
    )
    if price_includes_tax_default is None:
        price_includes_tax_default = None

    categories: list[dict[str, Any]] = []
    if tid:
        cats = db.query(ProductCategory).filter(ProductCategory.tenant_id == tid).all()
        categories = [{"id": str(c.id), "name": c.name, "description": c.description} for c in cats]
    if not categories and template_defaults.get("categories"):
        categories = [
            {"id": "", "name": c, "description": ""} for c in template_defaults["categories"]
        ]

    enabled_modules: list[str] = []
    if tid:
        rows = (
            db.query(CompanyModule, Module)
            .join(Module, CompanyModule.module_id == Module.id)
            .filter(CompanyModule.tenant_id == tid, CompanyModule.active.is_(True))
            .all()
        )
        enabled_modules = [_module_slug(mod) for _cm, mod in rows]

    if not enabled_modules:
        modules_cfg = settings_obj.get("modules") if isinstance(settings_obj, dict) else None
        if isinstance(modules_cfg, dict):
            enabled_modules = [
                _normalize_slug(k)
                for k, v in modules_cfg.items()
                if isinstance(v, dict) and v.get("enabled") is True
            ]

    pos_receipt_width = None
    if isinstance(pos_config, dict):
        receipt_cfg = pos_config.get("receipt") or {}
        if isinstance(receipt_cfg, dict):
            pos_receipt_width = receipt_cfg.get("width_mm")
    if pos_receipt_width is None and isinstance(template_pos, dict):
        pos_receipt_width = template_pos.get("receipt_width_mm")

    pos_return_window_days = None
    if isinstance(pos_config, dict):
        pos_return_window_days = pos_config.get("return_window_days")
    if pos_return_window_days is None and isinstance(template_pos, dict):
        pos_return_window_days = template_pos.get("return_window_days")

    tax_conf = (pos_config.get("tax") if isinstance(pos_config, dict) else {}) or {}
    price_includes_tax = bool(tax_conf.get("price_includes_tax", price_includes_tax_default))
    default_tax_rate = (
        settings_obj.get("iva_tasa_defecto")
        or tax_conf.get("default_rate")
        or (template_defaults.get("tax_rate") if isinstance(template_defaults, dict) else None)
    )
    if default_tax_rate is not None:
        try:
            default_tax_rate = float(default_tax_rate)
        except Exception:
            default_tax_rate = None

    features = {
        "inventory_expiry_tracking": bool(
            settings_obj.get(
                "inventory_expiry_tracking",
                template_inventory.get(
                    "enable_expiry_tracking",
                    False,
                ),
            )
        ),
        "inventory_lot_tracking": bool(
            settings_obj.get(
                "inventory_lot_tracking",
                template_inventory.get(
                    "enable_lot_tracking",
                    False,
                ),
            )
        ),
        "inventory_serial_tracking": bool(
            settings_obj.get(
                "inventory_serial_tracking",
                template_inventory.get(
                    "enable_serial_tracking",
                    False,
                ),
            )
        ),
        "inventory_auto_reorder": bool(
            settings_obj.get(
                "inventory_auto_reorder",
                template_inventory.get(
                    "auto_reorder",
                    False,
                ),
            )
        ),
        "pos_enable_weights": bool(
            pos_config.get("enable_weights", template_pos.get("enable_weights", False))
            if isinstance(pos_config, dict)
            else template_pos.get("enable_weights", False)
        ),
        "pos_enable_batch_tracking": bool(
            pos_config.get(
                "enable_batch_tracking", template_pos.get("enable_batch_tracking", False)
            )
            if isinstance(pos_config, dict)
            else template_pos.get("enable_batch_tracking", False)
        ),
        "pos_receipt_width_mm": int(pos_receipt_width) if pos_receipt_width is not None else None,
        "pos_return_window_days": int(pos_return_window_days)
        if pos_return_window_days is not None
        else None,
        "price_includes_tax": price_includes_tax,
        "tax_rate": default_tax_rate,
    }

    sector = {
        "plantilla": plantilla or "default",
        "features": sector_features,
    }

    data = {
        "tenant": {
            "id": str(tenant.id) if tenant else "",
            "name": tenant.name if tenant else "",
            "color_primario": (tenant.primary_color if tenant else None),
            "plantilla_inicio": (tenant.default_template if tenant else None),
            "currency": (currency or (tenant.base_currency if tenant else None)),
            "country": (tenant.country_code or tenant.country) if tenant else None,
            "config_json": (
                settings_obj.get("template_config") if isinstance(settings_obj, dict) else {}
            ),
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
