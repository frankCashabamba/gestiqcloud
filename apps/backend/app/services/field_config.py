from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from app.models.company.company import SectorTemplate


def _normalize(items: list[dict]) -> list[dict]:
    out: list[dict] = []
    for it in items or []:
        f = (it or {}).get("field")
        if not f:
            continue
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
                "validation_pattern": (it or {}).get("validation_pattern"),
                "validation_rules": (it or {}).get("validation_rules"),
                "transform_expression": (it or {}).get("transform_expression"),
            }
        )
    return out


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
        tpl = (
            db.query(SectorTemplate)
            .filter(
                SectorTemplate.code == sector.lower(),
                SectorTemplate.is_active == True,  # noqa: E712
            )
            .first()
        )
        if not tpl:
            return []
        config = tpl.template_config or {}
        branding = config.get("branding", {}) or {}
        required = (branding.get("required_fields", {}) or {}).get(module, [])
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

    # Load tenant overrides
    tenant_items: list[dict] = []
    if tenant_id:
        rows = (
            db.query(TenantFieldConfig)
            .filter(
                TenantFieldConfig.tenant_id == tenant_id,
                TenantFieldConfig.module == module,
            )
            .order_by(TenantFieldConfig.ord.asc().nulls_last())
            .all()
        )
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

            srows = (
                db.query(SectorFieldDefault)
                .filter(
                    SectorFieldDefault.sector == sector,
                    SectorFieldDefault.module == module,
                )
                .order_by(SectorFieldDefault.ord.asc().nulls_last())
                .all()
            )
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
                    "validation_pattern": getattr(r, "validation_pattern", None),
                    "validation_rules": getattr(r, "validation_rules", None),
                    "transform_expression": getattr(r, "transform_expression", None),
                }
                for r in srows
            ]
        except Exception:
            sector_items = []

    # Base code defaults (prioriza config de template del sector)
    template_items = _template_required_fields(db, sector, module)
    # Evitar hardcoding: si no hay datos en template ni defaults_fn, retorna vacío
    if defaults_fn is None:
        base_items = template_items
    else:
        base_items = template_items or _normalize(defaults_fn(module, sector or "default"))

    # Read mode
    mode = "mixed"
    if tenant_id:
        try:
            from sqlalchemy import text

            row = db.execute(
                text(
                    "SELECT form_mode FROM tenant_module_settings WHERE tenant_id = :tid AND module = :mod"
                ),
                {"tid": tenant_id, "mod": module},
            ).first()
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
