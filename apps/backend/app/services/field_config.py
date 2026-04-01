from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from app.models.company.company import SectorTemplate
from app.models.core.ui_field_config import SectorFieldDefault, UiFieldConfigScopeRule

_CLIENT_SECTOR_DEFAULTS: dict[str, list[dict[str, Any]]] = {
    "default": [
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
    ],
    "retail": [
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
        {"field": "whatsapp", "visible": True, "required": False, "ord": 40},
        {"field": "descuento_pct", "visible": True, "required": False, "ord": 41},
        {"field": "payment_terms_days", "visible": False, "required": False, "ord": 42},
        {"field": "credit_limit", "visible": False, "required": False, "ord": 43},
        {"field": "moneda", "visible": True, "required": False, "ord": 44},
    ],
    "panaderia": [
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
        {"field": "contacto_nombre", "visible": True, "required": False, "ord": 50},
        {"field": "contacto_telefono", "visible": True, "required": False, "ord": 51},
        {"field": "envio_direccion", "visible": False, "required": False, "ord": 60},
    ],
    "restaurante": [
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
    ],
    "taller": [
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
        {"field": "contacto_nombre", "visible": True, "required": False, "ord": 50},
        {"field": "contacto_telefono", "visible": True, "required": False, "ord": 51},
        {"field": "idioma", "visible": False, "required": False, "ord": 70},
    ],
}

_CLIENT_SECTOR_ALIASES = {
    "bazar": "retail",
    "todoa100": "retail",
    "panerp": "panaderia",
    "mecanico": "taller",
}

_FIELD_MODULE_ALIASES = {
    "customers": "clientes",
    "customer": "clientes",
    "clients": "clientes",
    "client": "clientes",
    "products": "productos",
    "product": "productos",
    "proveedores": "suppliers",
    "proveedor": "suppliers",
    "supplier": "suppliers",
}

def _normalize(items: list[dict]) -> list[dict]:
    out: list[dict] = []
    for it in items or []:
        f = (it or {}).get("field")
        if not f:
            continue
        options = (it or {}).get("options")
        if options is None:
            options = []
        out.append(
            {
                "field": f,
                "visible": bool((it or {}).get("visible", True)),
                "required": bool((it or {}).get("required", False)),
                "ord": (it or {}).get("ord"),
                "label": (it or {}).get("label"),
                "help": (it or {}).get("help"),
                # Campos opcionales para importador dinámico
                "aliases": (it or {}).get("aliases"),
                "field_type": (it or {}).get("field_type"),
                "options": options,
                "validation_pattern": (it or {}).get("validation_pattern"),
                "validation_rules": (it or {}).get("validation_rules"),
                "transform_expression": (it or {}).get("transform_expression"),
            }
        )
    return out


def canonical_sector_field_key(sector: str | None) -> str:
    """Resolución de código de sector usando solo el dict de código (sin BD). Mantener para backward-compat."""
    raw = str(sector or "default").strip().lower()
    return _CLIENT_SECTOR_ALIASES.get(raw, raw)


def resolve_sector_code(db: Session, sector: str | None) -> str:
    """Resolución de código de sector con prioridad BD (sector.code_aliases en system_defaults)."""
    raw = str(sector or "default").strip().lower()
    try:
        from app.services.system_defaults_service import get_system_default_json

        aliases: dict = get_system_default_json(db, "sector.code_aliases", {})
        if isinstance(aliases, dict) and raw in aliases:
            return str(aliases[raw])
    except Exception:
        pass
    return _CLIENT_SECTOR_ALIASES.get(raw, raw)


def canonical_field_module_key(module: str | None) -> str:
    raw = str(module or "").strip().lower()
    return _FIELD_MODULE_ALIASES.get(raw, raw)


def is_ui_field_config_scope(db: Session, module: str | None, sector: str | None = None) -> bool:
    raw_module = str(module or "").strip().lower()
    raw_sector = str(sector or "").strip().lower()
    try:
        rules = (
            db.query(UiFieldConfigScopeRule)
            .filter(
                UiFieldConfigScopeRule.active == True,  # noqa: E712
                UiFieldConfigScopeRule.action == "deny",
            )
            .all()
        )
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return True
    for rule in rules:
        if rule.scope_type == "sector_exact" and raw_sector == str(rule.scope_value or "").lower():
            return False
        if rule.scope_type == "module_prefix" and raw_module.startswith(
            str(rule.scope_value or "").lower()
        ):
            return False
    return True


def _field_module_candidates(module: str | None) -> list[str]:
    canonical = canonical_field_module_key(module)
    candidates = [canonical]
    for alias, target in _FIELD_MODULE_ALIASES.items():
        if target == canonical and alias not in candidates:
            candidates.append(alias)
    return candidates


def _template_field_items(db: Session, sector: str | None, module: str) -> list[dict]:
    sector_key = resolve_sector_code(db, sector)
    module_key = canonical_field_module_key(module)
    if not sector_key or not is_ui_field_config_scope(db, module_key, sector_key):
        return []
    try:
        tpl = (
            db.query(SectorTemplate)
            .filter(
                SectorTemplate.code == sector_key,
                SectorTemplate.is_active == True,  # noqa: E712
            )
            .first()
        )
        if not tpl:
            return []
        config = tpl.template_config or {}
        fields_cfg = (config.get("fields") or {}).get(module_key, {}) or {}
        items = fields_cfg.get("items") or fields_cfg.get("fields") or []
        if isinstance(items, dict):
            items = list(items.values())
        if not isinstance(items, list):
            return []
        return _normalize(items)
    except Exception:
        return []


def ensure_sector_field_defaults_seeded(db: Session, *, module: str, sector: str | None) -> None:
    """Seed DB-backed sector defaults for modules still migrating off code defaults."""
    module_candidates = _field_module_candidates(module)
    module_key = canonical_field_module_key(module)
    sector_key = resolve_sector_code(db, sector)
    if not is_ui_field_config_scope(db, module_key, sector_key):
        return

    exists = (
        db.query(SectorFieldDefault)
        .filter(
            SectorFieldDefault.sector == sector_key,
            SectorFieldDefault.module.in_(module_candidates),
        )
        .first()
    )
    if exists:
        return

    # Intenta cargar desde template_config del sector (BD); el dict hardcodeado
    # solo aplica como fallback para "clientes" mientras no haya datos en BD.
    items_to_seed: list[dict] = _template_field_items(db, sector_key, module_key)
    if not items_to_seed and module_key == "clientes":
        fallback_sector = sector_key if sector_key in _CLIENT_SECTOR_DEFAULTS else "default"
        items_to_seed = _normalize(_CLIENT_SECTOR_DEFAULTS[fallback_sector])

    if not items_to_seed:
        return

    for item in items_to_seed:
        db.add(
            SectorFieldDefault(
                sector=sector_key,
                module=module_key,
                field=item["field"],
                visible=item["visible"],
                required=item["required"],
                ord=item.get("ord"),
                label=item.get("label"),
                help=item.get("help"),
                field_type=item.get("field_type"),
                options=item.get("options"),
                validation_pattern=item.get("validation_pattern"),
            )
        )
    db.commit()


def _merge(base_items: list[dict], overrides: list[dict]) -> list[dict]:
    base = {str(it["field"]): {**it} for it in _normalize(base_items)}
    for o in _normalize(overrides):
        key = str(o["field"])
        if key in base:
            merged = {**base[key]}
            for k, v in o.items():
                if v is not None:
                    merged[k] = v
            if o.get("ord") is None and base[key].get("ord") is not None:
                merged["ord"] = base[key]["ord"]
            base[key] = merged
        else:
            base[key] = {**o}
    return sorted(
        base.values(),
        key=lambda x: (
            (x.get("ord") is None),
            (x.get("ord") or 9999),
            str(x.get("field")),
        ),
    )


def _template_required_fields(db: Session, sector: str | None, module: str) -> list[dict]:
    """Carga campos requeridos definidos en template_config del sector (si existen)."""
    if not sector:
        return []
    try:
        module_key = canonical_field_module_key(module)
        tpl = (
            db.query(SectorTemplate)
            .filter(
                SectorTemplate.code == resolve_sector_code(db, sector),
                SectorTemplate.is_active == True,  # noqa: E712
            )
            .first()
        )
        if not tpl:
            return []
        config = tpl.template_config or {}
        branding = config.get("branding", {}) or {}
        required = (branding.get("required_fields", {}) or {}).get(module_key, [])
        if not isinstance(required, list):
            return []
        return _normalize(
            [
                {
                    "field": f,
                    "required": True,
                    "visible": True,
                }
                for f in required
            ]
        )
    except Exception:
        return []


def resolve_fields(
    db: Session,
    *,
    module: str,
    tenant_id: str | None,
    sector: str | None,
    defaults_fn: Callable[[str, str], list[dict[str, Any]]] | None = None,
) -> list[dict]:
    """Resolve effective field list using form_mode.

    - Reads tenant overrides (tenant_field_config)
    - Reads sector defaults (sector_field_defaults)
    - Reads per-tenant mode from tenant_module_settings
    - Applies fallback strategy
    """
    from app.models.core.ui_field_config import TenantFieldConfig  # type: ignore

    module_key = canonical_field_module_key(module)
    module_candidates = _field_module_candidates(module)
    sector_key = resolve_sector_code(db, sector)
    if not is_ui_field_config_scope(db, module_key, sector_key):
        return []

    # Load tenant overrides
    tenant_items: list[dict] = []
    if tenant_id:
        rows = []
        try:
            for module_name in module_candidates:
                rows = (
                    db.query(TenantFieldConfig)
                    .filter(
                        TenantFieldConfig.tenant_id == tenant_id,
                        TenantFieldConfig.module == module_name,
                    )
                    .order_by(TenantFieldConfig.ord.asc().nulls_last())
                    .all()
                )
                if rows:
                    break
        except Exception:
            rows = []
        tenant_items = [
            {
                "field": r.field,
                "visible": bool(getattr(r, "visible", True)),
                "required": bool(getattr(r, "required", False)),
                "ord": getattr(r, "ord", None),
                "label": getattr(r, "label", None),
                "help": getattr(r, "help", None),
                "aliases": getattr(r, "aliases", None),
                "field_type": getattr(r, "field_type", None),
                "options": getattr(r, "options", None),
                "validation_pattern": getattr(r, "validation_pattern", None),
                "validation_rules": getattr(r, "validation_rules", None),
                "transform_expression": getattr(r, "transform_expression", None),
            }
            for r in rows
        ]

    # Load sector defaults
    sector_items: list[dict] = []
    if sector:
        try:
            from app.models.core.ui_field_config import SectorFieldDefault  # type: ignore

            srows = []
            for module_name in module_candidates:
                srows = (
                    db.query(SectorFieldDefault)
                    .filter(
                        SectorFieldDefault.sector == sector_key,
                        SectorFieldDefault.module == module_name,
                    )
                    .order_by(SectorFieldDefault.ord.asc().nulls_last())
                    .all()
                )
                if srows:
                    break
            sector_items = [
                {
                    "field": r.field,
                    "visible": bool(getattr(r, "visible", True)),
                    "required": bool(getattr(r, "required", False)),
                    "ord": getattr(r, "ord", None),
                    "label": getattr(r, "label", None),
                    "help": getattr(r, "help", None),
                    "aliases": getattr(r, "aliases", None),
                    "field_type": getattr(r, "field_type", None),
                    "options": getattr(r, "options", None),
                    "validation_pattern": getattr(r, "validation_pattern", None),
                    "validation_rules": getattr(r, "validation_rules", None),
                    "transform_expression": getattr(r, "transform_expression", None),
                }
                for r in srows
            ]
        except Exception:
            sector_items = []

    # Base code defaults (prioriza config de template del sector)
    template_items = _template_required_fields(db, sector_key, module_key)
    # Evitar hardcoding: si no hay datos en template ni defaults_fn, retorna vacío
    if defaults_fn is None:
        base_items = template_items
    else:
        base_items = template_items or _normalize(defaults_fn(module_key, sector_key or "default"))

    # Read mode
    mode = "mixed"
    if tenant_id:
        try:
            from sqlalchemy import text

            row = db.execute(
                text(
                    "SELECT form_mode FROM tenant_module_settings WHERE tenant_id = :tid AND module = :mod"
                ),
                {"tid": tenant_id, "mod": module_key},
            ).first()
            if (not row or not row[0]) and module_candidates:
                for legacy_module in module_candidates[1:]:
                    row = db.execute(
                        text(
                            "SELECT form_mode FROM tenant_module_settings "
                            "WHERE tenant_id = :tid AND module = :mod"
                        ),
                        {"tid": tenant_id, "mod": legacy_module},
                    ).first()
                    if row and row[0]:
                        break
            if row and row[0]:
                mode = str(row[0]).lower()
        except Exception:
            mode = "mixed"

    # Decide effective items
    if mode == "basic":
        return base_items or sector_items or tenant_items
    if mode == "sector":
        return sector_items or base_items
    if mode == "tenant":
        return tenant_items or sector_items or base_items
    # mixed (default): merge sector with tenant overrides
    source = sector_items or base_items
    return _merge(source, tenant_items)
