"""Catalog of available system modules with canonical IDs and legacy aliases."""

from __future__ import annotations

import json
import logging
import os
import unicodedata
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.core.module import Module

logger = logging.getLogger(__name__)


def _normalize_key(value: str | None) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    normalized = unicodedata.normalize("NFD", raw)
    without_marks = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return without_marks.replace(" ", "").replace("_", "").replace("-", "")


# Constante vacía mantenida para backward-compat de importaciones estáticas.
# En runtime SIEMPRE usar get_module_categories(db).
MODULE_CATEGORIES: list[dict[str, Any]] = []


def get_module_categories(db: Session) -> list[dict[str, Any]]:
    """Lee las categorías de módulos SIEMPRE desde system_defaults (BD).

    El seed inicial ocurre automáticamente la primera vez que se accede
    via ensure_system_defaults_table, por lo que la BD es siempre la fuente.
    """
    from app.services.system_defaults_service import get_system_default_json

    cats = get_system_default_json(db, "modules.categories", [])
    return cats if isinstance(cats, list) else []


# ---------------------------------------------------------------------------
# Filesystem-based module discovery
# ---------------------------------------------------------------------------


def _resolve_frontend_modules_dir() -> Path | None:
    from app.config.settings import settings

    cfg = getattr(settings, "FRONTEND_MODULES_PATH", None)
    if cfg and os.path.isdir(cfg):
        return Path(cfg)
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "apps").is_dir():
            for candidate in [
                parent / "apps" / "tenant" / "src" / "modules",
                parent / "apps" / "src" / "modules",
            ]:
                if candidate.is_dir():
                    return candidate
    return None


def _discover_modules_from_fs() -> list[dict[str, Any]]:
    """Scan module.json files from the frontend modules directory."""
    modules_dir = _resolve_frontend_modules_dir()
    if modules_dir is None:
        logger.warning(
            "Could not resolve frontend modules directory; module catalog will be empty."
        )
        return []

    result: list[dict[str, Any]] = []
    for child in sorted(modules_dir.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith(".") or child.name.startswith("_"):
            continue
        manifest = child / "module.json"
        if not manifest.is_file():
            continue
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except Exception:
            logger.warning("Failed to read %s, skipping", manifest)
            continue

        module_id = str(data.get("id") or child.name).strip()
        name = data.get("name", module_id)
        result.append(
            {
                "id": module_id,
                "name": name,
                "name_en": data.get("name_en", name),
                "icon": data.get("icon"),
                "category": data.get("category"),
                "description": data.get("description"),
                "required": bool(data.get("required", False)),
                "default_enabled": bool(data.get("default_enabled", True)),
                "dependencies": data.get("dependencies") or [],
                "countries": data.get("countries") or ["ES", "EC"],
                "sectors": data.get("sectors"),
                "aliases": data.get("aliases") or [],
                "implemented": bool(data.get("implemented", True)),
            }
        )

    return result


# ---------------------------------------------------------------------------
# Lazy-loaded lookup tables
# ---------------------------------------------------------------------------

_modules_loaded = False
_ALL_MODULES_BY_ID: dict[str, dict[str, Any]] = {}
_ALIASES_TO_ID: dict[str, str] = {}
AVAILABLE_MODULES: dict[str, dict[str, Any]] = {}


def _ensure_modules_loaded() -> None:
    global _modules_loaded
    if _modules_loaded:
        return
    _modules_loaded = True
    registry = _discover_modules_from_fs()
    for entry in registry:
        module = dict(entry)
        module_id = str(module["id"]).strip()
        aliases = {module_id, *(str(alias).strip() for alias in module.get("aliases", []))}
        module["aliases"] = sorted(alias for alias in aliases if alias)
        _ALL_MODULES_BY_ID[module_id] = module
        for alias in module["aliases"]:
            _ALIASES_TO_ID[_normalize_key(alias)] = module_id
    AVAILABLE_MODULES.update(
        {
            module_id: dict(module)
            for module_id, module in _ALL_MODULES_BY_ID.items()
            if bool(module.get("implemented", True))
        }
    )


def canonicalize_module_id(module_id: str | None) -> str | None:
    _ensure_modules_loaded()
    normalized = _normalize_key(module_id)
    if not normalized:
        return None
    return _ALIASES_TO_ID.get(normalized)


def get_module_aliases(module_id: str) -> list[str]:
    _ensure_modules_loaded()
    canonical = canonicalize_module_id(module_id) or str(module_id).strip().lower()
    module = _ALL_MODULES_BY_ID.get(canonical)
    if not module:
        return [canonical]
    return list(module.get("aliases", [canonical]))


def _module_catalog_id(module_row: Module) -> str | None:
    """Resuelve el catalog_id canónico de una fila de la tabla modules."""
    context_filters = getattr(module_row, "context_filters", None) or {}
    raw_candidates = [
        context_filters.get("catalog_id"),
        getattr(module_row, "url", None),
        getattr(module_row, "name", None),
    ]
    for raw in raw_candidates:
        canonical = canonicalize_module_id(raw)
        if canonical:
            return canonical
    return None


def _module_row_to_dict(row: Module) -> dict[str, Any]:
    """Convierte una fila de modules a dict normalizado."""
    catalog_id = _module_catalog_id(row) or str(getattr(row, "url", None) or row.name)
    return {
        "id": catalog_id,
        "name": row.name,
        "name_en": row.name,
        "icon": getattr(row, "icon", None),
        "category": getattr(row, "category", None),
        "description": getattr(row, "description", None),
        "active": bool(getattr(row, "active", True)),
        "implemented": bool(getattr(row, "implemented", True)),
        "required": bool(getattr(row, "required", False)),
        "default_enabled": bool(getattr(row, "default_enabled", True)),
        "dependencies": getattr(row, "dependencies", None) or [],
        "aliases": getattr(row, "aliases", None) or [catalog_id],
        "countries": getattr(row, "countries", None) or ["ES", "EC"],
        "sectors": getattr(row, "sectors", None),
    }


def ensure_module_catalog_seeded(db: Session) -> None:
    """Asegura que la tabla modules tenga las columnas nuevas y los módulos del sistema.

    1. Ejecuta ALTER TABLE para las 7 columnas nuevas (idempotente, IF NOT EXISTS).
    2. Si la tabla está vacía, siembra desde los module.json del filesystem.
    """
    from sqlalchemy import text

    _new_columns = [
        ("implemented", "BOOLEAN NOT NULL DEFAULT TRUE"),
        ("required", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("default_enabled", "BOOLEAN NOT NULL DEFAULT TRUE"),
        ("dependencies", "JSONB"),
        ("aliases", "JSONB"),
        ("countries", "JSONB"),
        ("sectors", "JSONB"),
    ]
    for col, definition in _new_columns:
        try:
            db.execute(text(f"ALTER TABLE modules ADD COLUMN IF NOT EXISTS {col} {definition}"))
        except Exception:
            db.rollback()
    try:
        db.commit()
    except Exception:
        db.rollback()

    if db.query(Module).count() > 0:
        return

    for entry in _discover_modules_from_fs():
        catalog_id = str(entry["id"])
        row = Module(
            name=catalog_id,
            description=entry.get("description"),
            active=True,
            icon=entry.get("icon"),
            url=catalog_id,
            initial_template=catalog_id,
            context_type="none",
            context_filters={"catalog_id": catalog_id},
            category=entry.get("category"),
        )
        for field in (
            "implemented",
            "required",
            "default_enabled",
            "dependencies",
            "aliases",
            "countries",
            "sectors",
        ):
            try:
                setattr(row, field, entry.get(field))
            except Exception:
                pass
        db.add(row)
    try:
        db.commit()
    except Exception:
        db.rollback()


def get_available_modules(
    country: str | None = None,
    sector: str | None = None,
    db: Session | None = None,
) -> list[dict[str, Any]]:
    """Retorna los módulos implementados del sistema.

    Fuente: tabla `modules` en BD (siempre, cuando hay sesión disponible).
    Fallback sin BD: catálogo del filesystem AVAILABLE_MODULES (tests / startup).
    """
    if db is None:
        _ensure_modules_loaded()
        modules = [dict(m) for m in AVAILABLE_MODULES.values()]
    else:
        ensure_module_catalog_seeded(db)
        rows = db.query(Module).filter(Module.active.is_(True), Module.implemented.is_(True)).all()
        modules = [_module_row_to_dict(row) for row in rows]

    if country:
        modules = [m for m in modules if country.upper() in (m.get("countries") or [])]
    if sector:
        modules = [
            m
            for m in modules
            if m.get("sectors") is None or sector.lower() in (m.get("sectors") or [])
        ]
    return modules


def get_module_by_id(module_id: str, db: Session | None = None) -> dict[str, Any] | None:
    canonical = canonicalize_module_id(module_id)
    if not canonical:
        return None
    for module in get_available_modules(db=db):
        if module.get("id") == canonical:
            return dict(module)
    return None


def get_required_modules(db: Session | None = None) -> list[str]:
    return [m["id"] for m in get_available_modules(db=db) if m.get("required")]


def get_default_enabled_modules(db: Session | None = None) -> list[str]:
    return [m["id"] for m in get_available_modules(db=db) if m.get("default_enabled")]


def validate_module_dependencies(enabled_modules: list[str]) -> dict[str, list[str]]:
    """Validate that enabled modules have their dependencies active."""
    _ensure_modules_loaded()
    canonical_enabled = {
        canonical
        for module_id in enabled_modules
        if (canonical := canonicalize_module_id(module_id))
    }
    missing_deps: dict[str, list[str]] = {}

    for module_id in canonical_enabled:
        module = AVAILABLE_MODULES.get(module_id)
        if not module:
            continue

        for dependency in module.get("dependencies", []):
            if dependency not in canonical_enabled:
                missing_deps.setdefault(module_id, []).append(dependency)

    return missing_deps
