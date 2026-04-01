"""
Sector defaults loader

Carga configuración de campos y categorías por sector desde base de datos
(`sector_field_defaults` y `sector_templates.template_config`). Eliminamos
hardcoding embebido en código; si no hay datos en BD, se retorna lista vacía.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.database import SessionLocal
from app.models.company.company import SectorTemplate
from app.models.core.ui_field_config import SectorFieldDefault
from app.services.field_config import (
    canonical_field_module_key,
    is_ui_field_config_scope,
    resolve_sector_code,
)


def _get_fallback_sector(session: Session) -> str:
    """Lee el sector de fallback desde system_defaults. Devuelve 'panaderia' si no está configurado."""
    try:
        row = session.execute(
            text("SELECT value_text FROM system_defaults WHERE key = 'sector.fallback_code'")
        ).fetchone()
        if row and row[0]:
            return str(row[0]).strip()
    except Exception:
        pass
    return "panaderia"


def _get_session(db: Session | None) -> tuple[Session, bool]:
    """Devuelve la sesión a usar y flag de cierre."""
    if db is not None:
        return db, False
    session = SessionLocal()
    return session, True


def _normalize_field_rows(rows: list[SectorFieldDefault]) -> list[dict[str, Any]]:
    return [
        {
            "field": r.field,
            "visible": bool(getattr(r, "visible", True)),
            "required": bool(getattr(r, "required", False)),
            "ord": getattr(r, "ord", None),
            "label": getattr(r, "label", None),
            "help": getattr(r, "help", None),
        }
        for r in rows
    ]


def _fields_from_template_config(tpl: SectorTemplate | None, module: str) -> list[dict[str, Any]]:
    if not tpl:
        return []
    config = tpl.template_config or {}
    fields_cfg = (config.get("fields") or {}).get(module, {}) or {}
    items = fields_cfg.get("items") or fields_cfg.get("fields") or []
    if isinstance(items, dict):
        items = list(items.values())
    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        field = item.get("field")
        if not field:
            continue
        normalized.append(
            {
                "field": field,
                "visible": bool(item.get("visible", True)),
                "required": bool(item.get("required", False)),
                "ord": item.get("ord"),
                "label": item.get("label"),
                "help": item.get("help"),
            }
        )
    return normalized


def get_sector_defaults(
    module: str, sector: str = "default", db: Session | None = None
) -> list[dict[str, Any]]:
    """
    Obtiene configuración de campos desde BD para un módulo y sector.
    Prioridad:
    1. sector_field_defaults
    2. template_config.fields en sector_templates
    3. Fallback a sector 'panaderia' si no hay datos para el sector solicitado
    """
    session, should_close = _get_session(db)
    try:
        sector_code = resolve_sector_code(session, sector)
        module_key = canonical_field_module_key(module)
        if not is_ui_field_config_scope(session, module_key, sector_code):
            return []
        module_candidates = [module_key]
        if module_key == "productos":
            module_candidates.append("products")
        elif module_key == "suppliers":
            module_candidates.append("proveedores")
        elif module_key == "clientes":
            module_candidates.extend(["customers", "clients"])

        def _load(code: str) -> tuple[list[dict[str, Any]], SectorTemplate | None]:
            tpl = (
                session.query(SectorTemplate)
                .filter(
                    SectorTemplate.code == code,
                    SectorTemplate.is_active == True,  # noqa: E712
                )
                .first()
            )
            rows: list[SectorFieldDefault] = []
            for module_name in module_candidates:
                rows = (
                    session.query(SectorFieldDefault)
                    .filter(
                        SectorFieldDefault.sector == code,
                        SectorFieldDefault.module == module_name,
                    )
                    .order_by(SectorFieldDefault.ord.asc().nulls_last())
                    .all()
                )
                if rows:
                    break
            return _normalize_field_rows(rows), tpl

        fields, tpl = _load(sector_code)

        if not fields:
            fields = _fields_from_template_config(tpl, module_key)

        # Fallback al sector configurado en system_defaults si no hay datos del sector solicitado
        fallback_sector = _get_fallback_sector(session)
        if not fields and sector_code != fallback_sector:
            fields, tpl_pan = _load(fallback_sector)
            if not fields:
                fields = _fields_from_template_config(tpl_pan, module_key)

        return fields
    finally:
        if should_close:
            session.close()


def get_sector_categories(
    sector: str, module: str = "productos", db: Session | None = None
) -> list[str]:
    """
    Obtiene categorías por defecto desde template_config.defaults.
    Soporta:
    - defaults.categories (productos)
    - defaults.expenses_categories (expenses)
    Fallback: categorías de panadería, luego ["General", "Otros"]
    """
    session, should_close = _get_session(db)
    try:
        sector_code = resolve_sector_code(session, sector)

        def _load_defaults(code: str) -> dict[str, Any]:
            tpl = (
                session.query(SectorTemplate)
                .filter(
                    SectorTemplate.code == code,
                    SectorTemplate.is_active == True,  # noqa: E712
                )
                .first()
            )
            return (tpl.template_config or {}).get("defaults", {}) if tpl else {}

        defaults = _load_defaults(sector_code)
        categories = []
        if module == "productos":
            categories = defaults.get("categories") or []
        elif module == "expenses":
            categories = defaults.get("expenses_categories") or []

        if categories:
            return categories

        fallback_sector = _get_fallback_sector(session)
        if sector_code != fallback_sector:
            defaults_pan = _load_defaults(fallback_sector)
            if module == "productos":
                categories = defaults_pan.get("categories") or []
            elif module == "expenses":
                categories = defaults_pan.get("expenses_categories") or []
            if categories:
                return categories

        return ["General", "Otros"]
    finally:
        if should_close:
            session.close()
