from __future__ import annotations

import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.models.core.ui_field_config import TenantFieldConfig
from app.models.core.ui_template import UiTemplate
from app.models.empresa.settings import ConfiguracionEmpresa
from app.models.tenant import Tenant as Empresa
from app.services.field_config import resolve_fields

from ...infrastructure.repositories import SettingsRepo

router = APIRouter()
admin_router = APIRouter(prefix="/admin/field-config", tags=["admin-field-config"])


@router.get("/general")
def get_general(db: Session = Depends(get_db)):
    return SettingsRepo(db).get("general")


@router.put("/general")
def put_general(payload: dict, db: Session = Depends(get_db)):
    SettingsRepo(db).put("general", payload)
    return {"ok": True}


@router.get("/branding")
def get_branding(db: Session = Depends(get_db)):
    return SettingsRepo(db).get("branding")


@router.put("/branding")
def put_branding(payload: dict, db: Session = Depends(get_db)):
    SettingsRepo(db).put("branding", payload)
    return {"ok": True}


@router.get("/fiscal")
def get_fiscal(db: Session = Depends(get_db)):
    return SettingsRepo(db).get("fiscal")


def _require_tenant_admin(claims: dict):
    # es_admin_empresa debe ser True para modificar settings sensibles
    try:
        if not isinstance(claims, dict) or not claims.get("es_admin_empresa", False):
            raise HTTPException(status_code=403, detail="admin_required")
    except Exception:
        raise HTTPException(status_code=403, detail="admin_required")


@router.put("/fiscal")
def put_fiscal(
    payload: dict,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    _require_tenant_admin(claims)
    SettingsRepo(db).put("fiscal", payload)
    return {"ok": True}


@router.put("/pos")
def put_pos_settings(
    payload: dict,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Actualizar ajustes POS (incluye tax.enabled/default_rate).

    Requiere es_admin_empresa=true en claims.
    """
    _require_tenant_admin(claims)
    SettingsRepo(db).put("pos", payload)
    return {"ok": True}


@router.get("/horarios")
def get_horarios(db: Session = Depends(get_db)):
    return SettingsRepo(db).get("horarios")


@router.put("/horarios")
def put_horarios(payload: dict, db: Session = Depends(get_db)):
    SettingsRepo(db).put("horarios", payload)
    return {"ok": True}


@router.get("/limites")
def get_limites(db: Session = Depends(get_db)):
    return SettingsRepo(db).get("limites")


@router.put("/limites")
def put_limites(payload: dict, db: Session = Depends(get_db)):
    SettingsRepo(db).put("limites", payload)
    return {"ok": True}


def _normalize_sector_slug(name: str | None) -> str | None:
    if not name:
        return None
    s = unicodedata.normalize("NFKD", name).encode("ASCII", "ignore").decode("ASCII")
    s = s.lower().strip()
    for suffix in (" artesanal", " general"):
        s = s.replace(suffix, "")
    return s.replace(" ", "") or None


def _canonical_sector_slug(name: str | None) -> str | None:
    """Map arbitrary sector labels to canonical slugs used by templates.

    Examples:
    - "Retail-Bazar" -> "retail"
    - "Bazar" -> "retail"
    - "Todo a 100" -> "retail"
    - "PanERP" -> "panaderia"
    - "Mecanico" -> "taller"
    """
    if not name:
        return None
    # Normalize accents and punctuation
    s = unicodedata.normalize("NFKD", name).encode("ASCII", "ignore").decode("ASCII")
    s = s.lower()
    # Replace non-alphanumeric with spaces, collapse
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    tokens = set(s.split())

    # Retail family
    if (
        {"retail", "bazar"} & tokens
        or "todoa100" in tokens
        or ("todo" in tokens and "100" in tokens)
    ):
        return "retail"

    # Panaderia family
    if "panaderia" in tokens or "panerp" in tokens:
        return "panaderia"

    # Taller / Mecanico family
    if "taller" in tokens or "mecanico" in tokens:
        return "taller"

    # Fallback to compact slug without spaces
    return s.replace(" ", "") or None


@router.get("/theme")
def get_theme_tokens(db: Session = Depends(get_db), empresa: str | None = Query(default=None)):
    """Return design tokens for theming the tenant UI.

    Usa `Tenant.sector_template_name` como fuente del sector (normalizado y
    con mapeos de compatibilidad: bazar/todoa100 -> retail, panerp -> panaderia,
    mecanico -> taller). Para colores, prioriza `ConfiguracionEmpresa.color_primario`
    y luego `Tenant.primary_color`.
    """
    if empresa:
        emp = (
            db.query(Empresa).filter((Empresa.slug == empresa) | (Empresa.name == empresa)).first()
        )
        cfg = None
        if emp:
            try:
                cfg = (
                    db.query(ConfiguracionEmpresa)
                    .filter(ConfiguracionEmpresa.tenant_id == emp.id)
                    .first()
                )
            except Exception:
                cfg = None

        brand_name = emp.name if emp else ""
        logo_url = (
            (getattr(cfg, "logo_empresa", None) or getattr(emp, "logo", None))
            if (cfg or emp)
            else None
        )
        color_primary = (
            getattr(cfg, "color_primario", None) or getattr(emp, "primary_color", None) or "#0ea5e9"
        )

        raw_sector = getattr(emp, "sector_template_name", None)
        sector = _canonical_sector_slug(raw_sector) or "default"

        return {
            "brand": {"name": brand_name, "logoUrl": logo_url, "faviconUrl": None},
            "colors": {
                "primary": color_primary,
                "onPrimary": "#ffffff",
                "bg": "#ffffff",
                "fg": "#0f172a",
                "muted": "#64748b",
                "success": "#10b981",
                "warning": "#f59e0b",
                "danger": "#ef4444",
            },
            "typography": {
                "fontFamily": "Inter, system-ui, sans-serif",
                "fontSizeBase": "16px",
            },
            "radius": {"sm": "4px", "md": "8px", "lg": "12px"},
            "shadows": {
                "sm": "0 1px 2px rgba(0,0,0,.08)",
                "md": "0 4px 12px rgba(0,0,0,.12)",
            },
            "mode": "light",
            "components": {},
            "sector": sector,
        }

    # Safe defaults
    return {
        "brand": {"name": "", "logoUrl": None, "faviconUrl": None},
        "colors": {
            "primary": "#0ea5e9",
            "onPrimary": "#ffffff",
            "bg": "#ffffff",
            "fg": "#0f172a",
            "muted": "#64748b",
            "success": "#10b981",
            "warning": "#f59e0b",
            "danger": "#ef4444",
        },
        "typography": {
            "fontFamily": "Inter, system-ui, sans-serif",
            "fontSizeBase": "16px",
        },
        "radius": {"sm": "4px", "md": "8px", "lg": "12px"},
        "shadows": {
            "sm": "0 1px 2px rgba(0,0,0,.08)",
            "md": "0 4px 12px rgba(0,0,0,.12)",
        },
        "mode": "light",
        "components": {},
    }


def _default_fields_by_sector(module: str, sector: str) -> list[dict]:
    """Default field visibility/order for known modules by sector.

    Currently supports module 'clientes'. Extend as needed.
    """
    sector = (sector or "default").lower()
    if module != "clientes":
        return []

    # Base fields common for all sectors
    base = [
        {"field": "nombre", "visible": True, "required": True, "ord": 10},
        {"field": "identificacion_tipo", "visible": True, "required": False, "ord": 15},
        {"field": "identificacion", "visible": True, "required": False, "ord": 16},
        {"field": "email", "visible": True, "required": False, "ord": 20},
        {"field": "telefono", "visible": True, "required": False, "ord": 21},
        {"field": "direccion", "visible": True, "required": False, "ord": 30},
        {"field": "direccion2", "visible": False, "required": False, "ord": 31},
        {"field": "localidad", "visible": True, "required": False, "ord": 32},
        {"field": "provincia", "visible": True, "required": False, "ord": 33},
        {"field": "ciudad", "visible": False, "required": False, "ord": 34},
        {"field": "pais", "visible": True, "required": False, "ord": 35},
        {"field": "codigo_postal", "visible": True, "required": False, "ord": 36},
    ]

    sector_extras: list[dict] = []
    if sector in ("retail", "bazar", "todoa100"):
        sector_extras += [
            {"field": "whatsapp", "visible": True, "required": False, "ord": 40},
            {"field": "descuento_pct", "visible": True, "required": False, "ord": 41},
            {
                "field": "payment_terms_days",
                "visible": False,
                "required": False,
                "ord": 42,
            },
            {"field": "credit_limit", "visible": False, "required": False, "ord": 43},
            {"field": "moneda", "visible": True, "required": False, "ord": 44},
        ]
    if sector in ("panaderia", "panerp"):
        sector_extras += [
            {"field": "contacto_nombre", "visible": True, "required": False, "ord": 50},
            {
                "field": "contacto_telefono",
                "visible": True,
                "required": False,
                "ord": 51,
            },
            {
                "field": "envio_direccion",
                "visible": False,
                "required": False,
                "ord": 60,
            },
        ]
    if sector in ("taller", "mecanico"):
        sector_extras += [
            {"field": "contacto_nombre", "visible": True, "required": False, "ord": 50},
            {
                "field": "contacto_telefono",
                "visible": True,
                "required": False,
                "ord": 51,
            },
            {"field": "idioma", "visible": False, "required": False, "ord": 70},
        ]

    return base + sector_extras


@router.get("/fields")
def get_field_config(
    module: str = Query(..., description="Module key, e.g., 'clientes'"),
    empresa: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Return field visibility/requirements for a module, scoped by tenant.

    If no explicit config stored for the tenant/module, returns sensible defaults
    based on the tenant sector (plantilla_inicio -> normalized sector).
    """
    tenant_id = None
    sector = "default"
    if empresa:
        emp = (
            db.query(Empresa).filter((Empresa.slug == empresa) | (Empresa.name == empresa)).first()
        )
        if emp:
            tenant_id = getattr(emp, "id", None)
            sector = _normalize_sector_slug(getattr(emp, "sector_plantilla_nombre", None)) or (
                (getattr(emp, "plantilla_inicio", None) or "default").strip().lower()
            )

    items = resolve_fields(
        db,
        module=module,
        tenant_id=str(tenant_id) if tenant_id else None,
        sector=sector,
        defaults_fn=_default_fields_by_sector,
    )

    return {"module": module, "empresa": empresa, "items": items}


@admin_router.get("/sector")
def get_sector_fields(
    module: str = Query(...), sector: str = Query(...), db: Session = Depends(get_db)
):
    from app.models.core.ui_field_config import SectorFieldDefault

    s = (sector or "default").strip().lower()
    rows = (
        db.query(SectorFieldDefault)
        .filter(SectorFieldDefault.sector == s, SectorFieldDefault.module == module)
        .order_by(SectorFieldDefault.ord.asc().nulls_last())
        .all()
    )
    items = [
        {
            "field": r.field,
            "visible": bool(r.visible),
            "required": bool(r.required),
            "ord": r.ord,
            "label": r.label,
            "help": r.help,
        }
        for r in rows
    ]
    if not items:
        items = _default_fields_by_sector(module, s)
    return {"module": module, "sector": s, "items": items}


@admin_router.put("/sector")
def put_sector_fields(payload: dict, db: Session = Depends(get_db)):
    from app.models.core.ui_field_config import SectorFieldDefault

    sector = (payload.get("sector") or "default").strip().lower()
    module = payload.get("module")
    items = payload.get("items") or []
    if not module:
        return {"ok": False, "error": "module is required"}
    # Upsert: clear and insert for simplicity
    db.query(SectorFieldDefault).filter(
        SectorFieldDefault.sector == sector, SectorFieldDefault.module == module
    ).delete()
    for it in items:
        row = SectorFieldDefault(
            sector=sector,
            module=module,
            field=it.get("field"),
            visible=bool(it.get("visible", True)),
            required=bool(it.get("required", False)),
            ord=it.get("ord"),
            label=it.get("label"),
            help=it.get("help"),
        )
        db.add(row)
    db.commit()
    return {"ok": True}


@admin_router.put("/tenant")
def put_tenant_fields(payload: dict, db: Session = Depends(get_db)):
    empresa = payload.get("empresa")
    module = payload.get("module")
    items = payload.get("items") or []
    if not module:
        return {"ok": False, "error": "module is required"}
    tenant_id = None
    if empresa:
        emp = (
            db.query(Empresa).filter((Empresa.slug == empresa) | (Empresa.name == empresa)).first()
        )
        tenant_id = getattr(emp, "id", None)
    if not tenant_id:
        return {"ok": False, "error": "empresa not found"}
    db.query(TenantFieldConfig).filter(
        TenantFieldConfig.tenant_id == tenant_id, TenantFieldConfig.module == module
    ).delete()
    for it in items:
        row = TenantFieldConfig(
            tenant_id=tenant_id,
            module=module,
            field=it.get("field"),
            visible=bool(it.get("visible", True)),
            required=bool(it.get("required", False)),
            ord=it.get("ord"),
            label=it.get("label"),
            help=it.get("help"),
        )
        db.add(row)
    db.commit()
    return {"ok": True}


@admin_router.get("/ui-plantillas")
def list_ui_templates_admin(db: Session = Depends(get_db)):
    """Lista plantillas UI (slugs disponibles) para uso en Admin.

    Ruta: /api/v1/admin/field-config/ui-plantillas
    """
    rows = (
        db.query(UiTemplate)
        .filter(UiTemplate.active == True)  # noqa: E712
        .order_by(UiTemplate.ord.asc().nulls_last(), UiTemplate.label.asc())
        .all()
    )
    items = [
        {
            "slug": r.slug,
            "label": r.label,
            "description": r.description,
            "pro": bool(r.pro),
            "active": bool(r.active),
            "ord": r.ord,
        }
        for r in rows
    ]
    return {"count": len(items), "items": items}


@admin_router.get("/ui-plantillas/health")
def ui_templates_health(request: Request):
    """Debug endpoint to verify router mounting and request URL resolution."""
    return {
        "ok": True,
        "url": str(request.url),
        "path": str(request.url.path),
        "base_url": str(request.base_url),
    }


@admin_router.put("/tenant/mode")
def put_tenant_module_mode(payload: dict, db: Session = Depends(get_db)):
    """Set per-tenant per-module form mode.

    payload: { empresa: slug|name, module: str, form_mode: 'mixed'|'tenant'|'sector'|'basic' }
    """
    empresa = payload.get("empresa")
    module = payload.get("module")
    form_mode = str(payload.get("form_mode") or "mixed").lower()
    if not module:
        return {"ok": False, "error": "module is required"}
    tenant_id = None
    if empresa:
        emp = (
            db.query(Empresa).filter((Empresa.slug == empresa) | (Empresa.name == empresa)).first()
        )
        tenant_id = getattr(emp, "id", None)
    if not tenant_id:
        return {"ok": False, "error": "empresa not found"}
    from sqlalchemy import text

    db.execute(
        text(
            """
            INSERT INTO tenant_module_settings(tenant_id, module, form_mode)
            VALUES (:tid, :mod, :mode)
            ON CONFLICT (tenant_id, module)
            DO UPDATE SET form_mode = EXCLUDED.form_mode, updated_at = NOW()
            """
        ),
        {"tid": tenant_id, "mod": module, "mode": form_mode},
    )
    db.commit()
    return {
        "ok": True,
        "tenant_id": str(tenant_id),
        "module": module,
        "form_mode": form_mode,
    }
