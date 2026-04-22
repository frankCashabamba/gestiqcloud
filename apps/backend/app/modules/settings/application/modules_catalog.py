"""Catalog of available system modules with canonical IDs."""

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

DEFAULT_MODULE_SURFACE = "business"
DEFAULT_MODULE_NAV_GROUP = "sidebar"
_RUNTIME_META_KEYS = ("surface", "nav_group", "contractable", "use_module_loader")
_HIERARCHY_META_KEYS = ("parent_module",)


def _coerce_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    return default


def _runtime_meta_from_entry(entry: dict[str, Any] | None) -> dict[str, Any]:
    source = entry or {}
    return {
        "surface": str(source.get("surface") or DEFAULT_MODULE_SURFACE),
        "nav_group": str(source.get("nav_group") or DEFAULT_MODULE_NAV_GROUP),
        "contractable": _coerce_bool(source.get("contractable"), True),
        "use_module_loader": _coerce_bool(source.get("use_module_loader"), True),
    }


def resolve_module_runtime_meta(
    module_id: str | None,
    *,
    context_filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _ensure_modules_loaded()
    canonical = canonicalize_module_id(module_id)
    entry = _ALL_MODULES_BY_ID.get(canonical or "")
    resolved = _runtime_meta_from_entry(entry)
    extra = context_filters or {}
    if "surface" in extra and extra["surface"]:
        resolved["surface"] = str(extra["surface"])
    if "nav_group" in extra and extra["nav_group"]:
        resolved["nav_group"] = str(extra["nav_group"])
    if "contractable" in extra:
        resolved["contractable"] = _coerce_bool(extra["contractable"], resolved["contractable"])
    if "use_module_loader" in extra:
        resolved["use_module_loader"] = _coerce_bool(
            extra["use_module_loader"], resolved["use_module_loader"]
        )
    return resolved


def resolve_module_parent(
    module_id: str | None,
    *,
    context_filters: dict[str, Any] | None = None,
) -> str | None:
    _ensure_modules_loaded()
    canonical = canonicalize_module_id(module_id)
    entry = _ALL_MODULES_BY_ID.get(canonical or "")
    parent = entry.get("parent_module") if entry else None
    extra = context_filters or {}
    if extra.get("parent_module"):
        parent = extra.get("parent_module")
    if parent is None:
        return None
    return str(parent)


def is_standalone_module(
    module_id: str | None,
    *,
    context_filters: dict[str, Any] | None = None,
) -> bool:
    return not resolve_module_parent(module_id, context_filters=context_filters)


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
                "implemented": bool(data.get("implemented", True)),
                "surface": data.get("surface") or DEFAULT_MODULE_SURFACE,
                "nav_group": data.get("nav_group") or DEFAULT_MODULE_NAV_GROUP,
                "contractable": _coerce_bool(data.get("contractable"), True),
                "use_module_loader": _coerce_bool(data.get("use_module_loader"), True),
                "parent_module": data.get("parent_module"),
            }
        )

    return result


# ---------------------------------------------------------------------------
# Static built-in registry — fallback when frontend filesystem is not available
# (e.g. production VPS where only the backend is deployed without frontend source)
# ---------------------------------------------------------------------------

_BUILTIN_MODULES: list[dict[str, Any]] = [
    {
        "id": "accounting",
        "name": "Accounting",
        "icon": "📚",
        "category": "finance",
        "description": "Ledger, journal entries and accounting controls",
        "required": False,
        "default_enabled": False,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "implemented": True,
    },
    {
        "id": "invoicing",
        "name": "Invoicing",
        "icon": "🧾",
        "category": "finance",
        "description": "Invoice management, credits and document numbering",
        "required": True,
        "default_enabled": True,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "implemented": True,
    },
    {
        "id": "copilot",
        "name": "RimayPilot",
        "icon": "✨",
        "category": "tools",
        "description": "AI analysis, suggestions and assisted draft creation with RimayPilot",
        "required": False,
        "default_enabled": False,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "implemented": False,
    },
    {
        "id": "crm",
        "name": "CRM",
        "icon": "🤝",
        "category": "sales",
        "description": "Lead management, opportunities and customer relations",
        "required": False,
        "default_enabled": True,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "implemented": True,
    },
    {
        "id": "customers",
        "name": "Customers",
        "icon": "🧑",
        "category": "sales",
        "description": "Customer records, segmentation and relationship management",
        "required": False,
        "default_enabled": True,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "implemented": True,
    },
    {
        "id": "einvoicing",
        "name": "E-Invoicing",
        "icon": "📨",
        "category": "finance",
        "description": "Electronic submission via SRI (EC) or Facturae/SII (ES)",
        "required": False,
        "default_enabled": True,
        "dependencies": ["invoicing"],
        "countries": ["ES", "EC"],
        "implemented": True,
        "contractable": True,
        "parent_module": "settings",
    },
    {
        "id": "expenses",
        "name": "Expenses",
        "icon": "💸",
        "category": "finance",
        "description": "Recording and approval of expenses, mileage and per diems",
        "required": False,
        "default_enabled": True,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "implemented": True,
    },
    {
        "id": "finance",
        "name": "Finance",
        "icon": "💼",
        "category": "finance",
        "description": "Cash, banks and treasury operations",
        "required": False,
        "default_enabled": True,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "implemented": True,
    },
    {
        "id": "hr",
        "name": "Human Resources",
        "icon": "👥",
        "category": "people",
        "description": "Payroll, attendance, vacations and contracts",
        "required": False,
        "default_enabled": False,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "implemented": True,
    },
    {
        "id": "imports",
        "name": "Imports",
        "icon": "📥",
        "category": "operations",
        "description": "Bulk loading of products, customers and data via Excel/CSV",
        "required": False,
        "default_enabled": True,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "implemented": True,
    },
    {
        "id": "inventory",
        "name": "Inventory",
        "icon": "📦",
        "category": "operations",
        "description": "Stock management, warehouses, lots and expiration dates",
        "required": False,
        "default_enabled": True,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "implemented": True,
    },
    {
        "id": "notifications",
        "name": "Notifications",
        "icon": "🔔",
        "category": "integrations",
        "description": "Notification center and alert management",
        "required": False,
        "default_enabled": False,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "implemented": True,
        "parent_module": "settings",
    },
    {
        "id": "pos",
        "name": "Point of Sale",
        "icon": "💰",
        "category": "sales",
        "description": "POS system with tickets, fast invoicing and thermal printing",
        "required": False,
        "default_enabled": True,
        "dependencies": ["inventory", "invoicing"],
        "countries": ["ES", "EC"],
        "implemented": True,
    },
    {
        "id": "manufacturing",
        "name": "Manufacturing",
        "icon": "🏭",
        "category": "operations",
        "description": "Production orders, BOM and manufacturing tracking",
        "required": False,
        "default_enabled": False,
        "dependencies": ["inventory"],
        "countries": ["ES", "EC"],
        "implemented": True,
    },
    {
        "id": "products",
        "name": "Products",
        "icon": "🏷️",
        "category": "operations",
        "description": "Product catalog, variants, labels and commercial data",
        "required": False,
        "default_enabled": True,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "implemented": True,
    },
    {
        "id": "purchases",
        "name": "Purchases",
        "icon": "🛒",
        "category": "operations",
        "description": "Purchase orders, receiving, and supplier management",
        "required": False,
        "default_enabled": True,
        "dependencies": ["inventory"],
        "countries": ["ES", "EC"],
        "implemented": True,
    },
    {
        "id": "reconciliation",
        "name": "Reconciliation",
        "icon": "🔄",
        "category": "finance",
        "description": "Bank statement import and reconciliation workflows",
        "required": False,
        "default_enabled": False,
        "dependencies": ["finance"],
        "countries": ["ES", "EC"],
        "implemented": True,
        "parent_module": "settings",
    },
    {
        "id": "reports",
        "name": "Reports",
        "icon": "📊",
        "category": "analytics",
        "description": "Custom reports, dashboards and exports",
        "required": False,
        "default_enabled": True,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "implemented": True,
    },
    {
        "id": "sales",
        "name": "Sales",
        "icon": "📈",
        "category": "sales",
        "description": "Quotes, orders, delivery notes and sales tracking",
        "required": False,
        "default_enabled": True,
        "dependencies": ["inventory", "invoicing"],
        "countries": ["ES", "EC"],
        "implemented": True,
    },
    {
        "id": "settings",
        "name": "Settings",
        "icon": "⚙️",
        "category": "settings",
        "description": "General configuration, branding, fiscal and operations settings",
        "required": False,
        "default_enabled": False,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "implemented": True,
    },
    {
        "id": "suppliers",
        "name": "Suppliers",
        "icon": "🚚",
        "category": "operations",
        "description": "Supplier profiles, contacts and purchasing workflows",
        "required": False,
        "default_enabled": True,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "implemented": True,
    },
    {
        "id": "templates",
        "name": "Templates",
        "icon": "🧩",
        "category": "settings",
        "description": "UI templates and overlay configuration",
        "required": False,
        "default_enabled": False,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "implemented": True,
        "parent_module": "settings",
    },
    {
        "id": "users",
        "name": "Users",
        "icon": "🪪",
        "category": "people",
        "description": "Tenant users, access roles and operational permissions",
        "required": False,
        "default_enabled": False,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "implemented": True,
        "contractable": True,
        "parent_module": "settings",
    },
    {
        "id": "webhooks",
        "name": "Webhooks",
        "icon": "🔗",
        "category": "integrations",
        "description": "Webhook subscriptions, delivery logs and integrations",
        "required": False,
        "default_enabled": False,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "implemented": True,
        "parent_module": "settings",
    },
    {
        "id": "historical",
        "name": "Historical",
        "icon": "📦",
        "category": "operations",
        "description": "Import and query historical data (sales, purchases, stock) without affecting real accounting",
        "required": False,
        "default_enabled": True,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "implemented": True,
        "surface": "backoffice",
        "nav_group": "backoffice",
        "contractable": True,
    },
]


# ---------------------------------------------------------------------------
# Lazy-loaded lookup tables
# ---------------------------------------------------------------------------

_modules_loaded = False
_ALL_MODULES_BY_ID: dict[str, dict[str, Any]] = {}
AVAILABLE_MODULES: dict[str, dict[str, Any]] = {}


def _ensure_modules_loaded() -> None:
    global _modules_loaded
    # If previously loaded but resulted in empty (e.g. filesystem not available at startup),
    # allow a retry so the built-in fallback can populate the tables.
    if _modules_loaded and _ALL_MODULES_BY_ID:
        return
    _modules_loaded = True
    registry = _discover_modules_from_fs()
    if not registry:
        # Filesystem not available (e.g. production VPS without frontend source) → use built-in
        logger.info("Frontend modules dir not found; using built-in static module registry.")
        registry = list(_BUILTIN_MODULES)
    for entry in registry:
        module = dict(entry)
        module_id = str(module["id"]).strip()
        _ALL_MODULES_BY_ID[module_id] = module
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
    if not normalized or normalized not in _ALL_MODULES_BY_ID:
        return None
    return normalized




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
    context_filters = getattr(row, "context_filters", None) or {}
    catalog_entry = _ALL_MODULES_BY_ID.get(catalog_id) or {}
    runtime_meta = resolve_module_runtime_meta(catalog_id, context_filters=context_filters)
    return {
        "id": catalog_id,
        "name": getattr(row, "name", None) or catalog_entry.get("name") or catalog_id,
        "name_en": getattr(row, "name", None) or catalog_entry.get("name") or catalog_id,
        "icon": getattr(row, "icon", None) or catalog_entry.get("icon"),
        "category": getattr(row, "category", None) or catalog_entry.get("category"),
        "description": getattr(row, "description", None) or catalog_entry.get("description"),
        "active": bool(getattr(row, "active", True)),
        "implemented": bool(getattr(row, "implemented", catalog_entry.get("implemented", True))),
        "required": bool(getattr(row, "required", catalog_entry.get("required", False))),
        "default_enabled": bool(
            getattr(row, "default_enabled", catalog_entry.get("default_enabled", True))
        ),
        "dependencies": getattr(row, "dependencies", None)
        or catalog_entry.get("dependencies")
        or [],
        "countries": getattr(row, "countries", None)
        or catalog_entry.get("countries")
        or ["ES", "EC"],
        "sectors": getattr(row, "sectors", None) or catalog_entry.get("sectors"),
        **runtime_meta,
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

    seed_entries = _discover_modules_from_fs() or list(_BUILTIN_MODULES)
    for entry in seed_entries:
        catalog_id = str(entry["id"])
        row = Module(
            name=catalog_id,
            description=entry.get("description"),
            active=True,
            icon=entry.get("icon"),
            url=catalog_id,
            initial_template=catalog_id,
            context_type="none",
            context_filters={
                "catalog_id": catalog_id,
                **{
                    key: entry.get(key)
                    for key in (*_RUNTIME_META_KEYS, *_HIERARCHY_META_KEYS)
                    if key in entry
                },
            },
            category=entry.get("category"),
        )
        for field in (
            "implemented",
            "required",
            "default_enabled",
            "dependencies",
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
