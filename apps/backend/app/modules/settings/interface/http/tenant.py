from __future__ import annotations

import os
import re
import unicodedata
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import text
from sqlalchemy import text as sa_text
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.jwt_provider import get_token_service
from app.models.company.company_settings import CompanySettings
from app.models.company.settings import ConfiguracionEmpresa
from app.models.core.ui_field_config import SectorFieldDefault, TenantFieldConfig
from app.models.core.ui_template import UiTemplate
from app.models.tenant import Tenant as Empresa
from app.services.field_config import (
    canonical_field_module_key,
    ensure_sector_field_defaults_seeded,
    resolve_fields,
    resolve_sector_code,
)
from app.services.sector_defaults import get_sector_defaults
from app.services.system_defaults_service import get_system_default_text

router = APIRouter()
admin_router = APIRouter(prefix="/admin/field-config", tags=["admin-field-config"])
token_service = get_token_service()


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


def _first_non_empty(*values: str | None) -> str | None:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str):
            v = value.strip()
            if v:
                return v
            continue
        return value
    return None


def _request_access_claims(request: Request | None) -> dict[str, object] | None:
    if request is None:
        return None

    auth = (request.headers.get("Authorization") or "").strip()
    token = auth.split(" ", 1)[1].strip() if auth.startswith("Bearer ") else ""
    if not token:
        token = (request.cookies.get("access_token") or "").strip()
    if not token:
        return None

    try:
        claims = token_service.decode_and_validate(token, expected_type="access")
    except Exception:
        return None
    return claims if isinstance(claims, dict) else None


def _request_tenant_id(request: Request | None) -> UUID | None:
    claims = _request_access_claims(request)
    tenant_id = claims.get("tenant_id") if isinstance(claims, dict) else None
    if not tenant_id:
        return None
    try:
        return UUID(str(tenant_id))
    except (TypeError, ValueError):
        return None


def _lookup_empresa(db: Session, empresa: str | None) -> Empresa | None:
    if not empresa:
        return None
    return (
        db.query(Empresa).filter(Empresa.slug == empresa).order_by(Empresa.created_at.asc()).first()
    )


def _resolve_empresa(
    db: Session,
    *,
    request: Request | None = None,
    empresa: str | None = None,
) -> Empresa | None:
    tenant_id = _request_tenant_id(request)
    if tenant_id:
        emp = db.query(Empresa).filter(Empresa.id == tenant_id).first()
        if emp:
            if empresa and getattr(emp, "slug", None) and str(emp.slug) != str(empresa):
                raise HTTPException(status_code=403, detail="tenant_slug_mismatch")
            return emp
        if empresa:
            raise HTTPException(status_code=401, detail="tenant_auth_required")
        return None
    if empresa:
        raise HTTPException(status_code=401, detail="tenant_auth_required")
    return None


def _theme_defaults(db: Session) -> dict[str, object]:
    return {
        "colors": {
            "primary": get_system_default_text(db, "theme.colors.primary", "#2563eb"),
            "secondary": get_system_default_text(db, "theme.colors.secondary", "#1e293b"),
            "onPrimary": get_system_default_text(db, "theme.colors.on_primary", "#ffffff"),
            "bg": get_system_default_text(db, "theme.colors.bg", "#ffffff"),
            "fg": get_system_default_text(db, "theme.colors.fg", "#0f172a"),
            "muted": get_system_default_text(db, "theme.colors.muted", "#64748b"),
            "success": get_system_default_text(db, "theme.colors.success", "#10b981"),
            "warning": get_system_default_text(db, "theme.colors.warning", "#f59e0b"),
            "danger": get_system_default_text(db, "theme.colors.danger", "#ef4444"),
        },
        "typography": {
            "fontFamily": get_system_default_text(
                db, "theme.typography.font_family", "Inter, system-ui, sans-serif"
            ),
            "fontSizeBase": get_system_default_text(db, "theme.typography.font_size_base", "16px"),
        },
        "radius": {
            "sm": get_system_default_text(db, "theme.radius.sm", "4px"),
            "md": get_system_default_text(db, "theme.radius.md", "8px"),
            "lg": get_system_default_text(db, "theme.radius.lg", "12px"),
        },
        "shadows": {
            "sm": get_system_default_text(db, "theme.shadows.sm", "0 1px 2px rgba(0,0,0,.08)"),
            "md": get_system_default_text(db, "theme.shadows.md", "0 4px 12px rgba(0,0,0,.12)"),
        },
    }


@router.get("/theme")
def get_theme_tokens(
    request: Request,
    db: Session = Depends(get_db),
    empresa: str | None = Query(default=None),
):
    """Return design tokens for theming the tenant UI.

    Usa `Tenant.sector_template_name` como fuente del sector (normalizado y
    con mapeos de compatibilidad: bazar/todoa100 -> retail, panerp -> panaderia,
    mecanico -> taller). Para colores, prioriza `ConfiguracionEmpresa.color_primario`
    y luego `Tenant.primary_color`.
    """
    defaults = _theme_defaults(db)

    emp = _resolve_empresa(db, request=request, empresa=empresa)
    if emp:
        cfg = None
        try:
            cfg = (
                db.query(ConfiguracionEmpresa)
                .filter(ConfiguracionEmpresa.tenant_id == emp.id)
                .first()
            )
        except Exception:
            cfg = None
        company_settings = None
        try:
            company_settings = (
                db.query(CompanySettings).filter(CompanySettings.tenant_id == emp.id).first()
            )
        except Exception:
            company_settings = None

        brand_name = emp.name if emp else ""
        logo_url = _first_non_empty(
            company_settings.company_logo if company_settings else None,
            getattr(cfg, "logo_empresa", None),
            getattr(emp, "logo", None),
        )
        color_primary = _first_non_empty(
            company_settings.primary_color if company_settings else None,
            getattr(cfg, "color_primario", None),
            getattr(emp, "primary_color", None),
            str(defaults["colors"]["primary"]),
        )
        color_secondary = _first_non_empty(
            company_settings.secondary_color if company_settings else None,
            getattr(cfg, "color_secundario", None),
            str(defaults["colors"]["secondary"]),
        )

        raw_sector = getattr(emp, "sector_template_name", None)
        sector = _canonical_sector_slug(raw_sector) or "default"

        return {
            "brand": {"name": brand_name, "logoUrl": logo_url, "faviconUrl": None},
            "colors": {
                "primary": color_primary,
                "secondary": color_secondary,
                "onPrimary": defaults["colors"]["onPrimary"],
                "bg": defaults["colors"]["bg"],
                "fg": defaults["colors"]["fg"],
                "muted": defaults["colors"]["muted"],
                "success": defaults["colors"]["success"],
                "warning": defaults["colors"]["warning"],
                "danger": defaults["colors"]["danger"],
            },
            "typography": defaults["typography"],
            "radius": defaults["radius"],
            "shadows": defaults["shadows"],
            "mode": "light",
            "components": {},
            "sector": sector,
        }

    # Safe defaults
    return {
        "brand": {"name": "", "logoUrl": None, "faviconUrl": None},
        "colors": defaults["colors"],
        "typography": defaults["typography"],
        "radius": defaults["radius"],
        "shadows": defaults["shadows"],
        "mode": "light",
        "components": {},
    }


@router.get("/fields")
def get_field_config(
    request: Request,
    module: str = Query(..., description="Module key, e.g., 'clientes'"),
    empresa: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Return field visibility/requirements for a module, scoped by tenant.

    If no explicit config stored for the tenant/module, returns sensible defaults
    based on the tenant sector (plantilla_inicio -> normalized sector).
    """
    requested_module = module
    module = canonical_field_module_key(module)
    tenant_id = None
    sector = "default"
    emp = _resolve_empresa(db, request=request, empresa=empresa)
    if emp:
        tenant_id = getattr(emp, "id", None)
        raw_sector = (
            getattr(emp, "sector_template_name", None)
            or getattr(emp, "sector_plantilla_nombre", None)
            or getattr(emp, "plantilla_inicio", None)
            or "default"
        )
        sector = resolve_sector_code(db, raw_sector)

    ensure_sector_field_defaults_seeded(db, module=module, sector=sector)

    items = resolve_fields(
        db,
        module=module,
        tenant_id=str(tenant_id) if tenant_id else None,
        sector=sector,
        defaults_fn=lambda mod, sec: get_sector_defaults(mod, sec, db=db),
    )

    return {
        "module": module,
        "requested_module": requested_module,
        "empresa": empresa,
        "items": items,
    }


@admin_router.get("/sector")
def get_sector_fields(
    module: str = Query(...), sector: str = Query(...), db: Session = Depends(get_db)
):
    from app.models.core.ui_field_config import SectorFieldDefault

    requested_module = module
    module = canonical_field_module_key(module)
    s = resolve_sector_code(db, sector)
    ensure_sector_field_defaults_seeded(db, module=module, sector=s)
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
            "field_type": getattr(r, "field_type", None),
            "options": getattr(r, "options", None),
            "validation_pattern": getattr(r, "validation_pattern", None),
        }
        for r in rows
    ]
    return {"module": module, "requested_module": requested_module, "sector": s, "items": items}


@admin_router.put("/sector")
def put_sector_fields(payload: dict, db: Session = Depends(get_db)):
    from app.models.core.ui_field_config import SectorFieldDefault

    sector = resolve_sector_code(db, payload.get("sector"))
    module = canonical_field_module_key(payload.get("module"))
    items = payload.get("items") or []
    if not module:
        return {"ok": False, "error": "module is required"}
    # Upsert: clear and insert for simplicity
    db.query(SectorFieldDefault).filter(
        SectorFieldDefault.sector == sector, SectorFieldDefault.module == module
    ).delete()
    for it in items:
        options = it.get("options")
        if options is None:
            options = []
        row = SectorFieldDefault(
            sector=sector,
            module=module,
            field=it.get("field"),
            visible=bool(it.get("visible", True)),
            required=bool(it.get("required", False)),
            ord=it.get("ord"),
            label=it.get("label"),
            help=it.get("help"),
            field_type=it.get("field_type"),
            options=options,
            validation_pattern=it.get("validation_pattern"),
        )
        db.add(row)
    db.commit()
    return {"ok": True}


@admin_router.put("/tenant")
def put_tenant_fields(payload: dict, db: Session = Depends(get_db)):
    empresa = payload.get("empresa")
    module = canonical_field_module_key(payload.get("module"))
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
        options = it.get("options")
        if options is None:
            options = []
        row = TenantFieldConfig(
            tenant_id=tenant_id,
            module=module,
            field=it.get("field"),
            visible=bool(it.get("visible", True)),
            required=bool(it.get("required", False)),
            ord=it.get("ord"),
            label=it.get("label"),
            help=it.get("help"),
            field_type=it.get("field_type"),
            options=options,
            validation_pattern=it.get("validation_pattern"),
        )
        db.add(row)
    db.commit()
    return {"ok": True}


def _allowed_import_tables() -> dict[str, str]:
    """
    Fuente de verdad configurable por env:
      IMPORTS_TABLE_WHITELIST=""
    Si no se define, se permite cualquier tabla y se usa imports_<tabla> como módulo por defecto.
    """
    env_val = os.getenv("IMPORTS_TABLE_WHITELIST", "").strip()
    if not env_val:
        return {}
    mapping: dict[str, str] = {}
    for item in env_val.split(","):
        if not item:
            continue
        parts = item.split(":")
        table = parts[0].strip().lower()
        module = parts[1].strip() if len(parts) > 1 and parts[1].strip() else f"imports_{table}"
        if table:
            mapping[table] = module
    return mapping


@admin_router.get("/import-tables")
def list_import_tables(db: Session = Depends(get_db)):
    """
    Lista tablas importables.

    - Si IMPORTS_TABLE_WHITELIST está seteado, devuelve ese listado (tabla -> módulo).
    - Si no, devuelve todas las tablas visibles del esquema actual (excluye pg_catalog, information_schema).
    """
    wl = _allowed_import_tables()
    if wl:
        items = [{"table": t, "module": m} for t, m in wl.items()]
        return {"items": items}

    rows = db.execute(
        sa_text(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog','information_schema')
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
        )
    ).fetchall()
    items = [{"table": r[0], "module": f"imports_{r[0]}"} for r in rows]
    # Fallback si no hay tablas visibles (p.ej. permisos restrictivos): usa lista mínima estándar
    if not items:
        defaults = ["products", "invoices", "expenses", "bank_transactions", "generic"]
        items = [{"table": t, "module": f"imports_{t}"} for t in defaults]
    return {"items": items}


def _guess_field_type(data_type: str | None) -> str | None:
    if not data_type:
        return None
    dt = data_type.lower()
    if any(x in dt for x in ("int", "numeric", "decimal", "double", "real", "money")):
        return "number"
    if "bool" in dt:
        return "boolean"
    if "date" in dt or "time" in dt:
        return "date"
    return "string"


@admin_router.post("/import-table")
def import_fields_from_table(payload: dict, db: Session = Depends(get_db)):
    """
    Importa columnas de una tabla whitelisted y las graba como SectorFieldDefault.

    payload: { table: 'products', module?: 'imports_products', sector?: 'global' }
    """
    table = (payload.get("table") or "").strip().lower()
    module = (payload.get("module") or "").strip()
    sector = (payload.get("sector") or "global").strip() or "global"
    if not table:
        return {"ok": False, "error": "table is required"}
    whitelist = _allowed_import_tables()
    if whitelist:
        if table not in whitelist:
            return {"ok": False, "error": "table not allowed"}
        if not module:
            module = whitelist.get(table)
    # Forzar módulo canónico imports_<tabla> si no viene o no es imports_*
    if not module or not module.startswith("imports_"):
        module = f"imports_{table}"
    # Leer columnas de information_schema (solo nombres/tipos)
    rows = db.execute(
        text(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = :tbl
              AND table_schema NOT IN ('information_schema','pg_catalog')
            ORDER BY ordinal_position
            """
        ),
        {"tbl": table},
    ).fetchall()
    if not rows:
        return {"ok": False, "error": "table has no columns or not found"}
    # Limpiar existentes y grabar nuevos
    db.query(SectorFieldDefault).filter(
        SectorFieldDefault.sector == sector, SectorFieldDefault.module == module
    ).delete()
    items = []
    for idx, r in enumerate(rows):
        fname = str(r[0])
        ftype = _guess_field_type(r[1])
        required = str(r[2]).lower() == "no"
        row = SectorFieldDefault(
            sector=sector,
            module=module,
            field=fname,
            visible=True,
            required=required,
            ord=idx,
            field_type=ftype,
        )
        db.add(row)
        items.append(
            {
                "field": fname,
                "visible": True,
                "required": required,
                "ord": idx,
                "field_type": ftype,
            }
        )
    db.commit()
    return {"ok": True, "items": items, "module": module, "sector": sector}


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
    module = canonical_field_module_key(payload.get("module"))
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
