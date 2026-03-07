"""Catalog of available system modules with canonical IDs and legacy aliases."""

from __future__ import annotations

import unicodedata
from typing import Any


def _normalize_key(value: str | None) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    normalized = unicodedata.normalize("NFD", raw)
    without_marks = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return without_marks.replace(" ", "").replace("_", "").replace("-", "")


MODULE_CATEGORIES = [
    {"id": "sales", "name": "Sales", "icon": "📈", "order": 1},
    {"id": "operations", "name": "Operations", "icon": "⚙️", "order": 2},
    {"id": "finance", "name": "Finance", "icon": "💼", "order": 3},
    {"id": "people", "name": "People", "icon": "👥", "order": 4},
    {"id": "settings", "name": "Settings", "icon": "⚙️", "order": 5},
    {"id": "integrations", "name": "Integrations", "icon": "🔌", "order": 6},
    {"id": "analytics", "name": "Analytics", "icon": "📊", "order": 7},
    {"id": "tools", "name": "Tools", "icon": "🧠", "order": 8},
]


MODULE_REGISTRY: list[dict[str, Any]] = [
    {
        "id": "pos",
        "name": "Point of Sale",
        "name_en": "Point of Sale",
        "icon": "💰",
        "category": "sales",
        "description": "POS system with tickets, fast invoicing and thermal printing",
        "required": False,
        "default_enabled": True,
        "dependencies": ["inventory", "invoicing"],
        "countries": ["ES", "EC"],
        "sectors": None,
        "aliases": ["tpv"],
        "implemented": True,
    },
    {
        "id": "inventory",
        "name": "Inventory",
        "name_en": "Inventory",
        "icon": "📦",
        "category": "operations",
        "description": "Stock management, warehouses, lots and expiration dates",
        "required": False,
        "default_enabled": True,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "sectors": None,
        "aliases": ["inventario"],
        "implemented": True,
    },
    {
        "id": "products",
        "name": "Products",
        "name_en": "Products",
        "icon": "🏷️",
        "category": "operations",
        "description": "Product catalog, variants, labels and commercial data",
        "required": False,
        "default_enabled": True,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "sectors": None,
        "aliases": ["productos"],
        "implemented": True,
    },
    {
        "id": "sales",
        "name": "Sales",
        "name_en": "Sales",
        "icon": "📈",
        "category": "sales",
        "description": "Quotes, orders, delivery notes and sales tracking",
        "required": False,
        "default_enabled": True,
        "dependencies": ["inventory", "invoicing"],
        "countries": ["ES", "EC"],
        "sectors": None,
        "aliases": ["ventas"],
        "implemented": True,
    },
    {
        "id": "customers",
        "name": "Customers",
        "name_en": "Customers",
        "icon": "🧑",
        "category": "sales",
        "description": "Customer records, segmentation and relationship management",
        "required": False,
        "default_enabled": True,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "sectors": None,
        "aliases": ["clientes", "clients"],
        "implemented": True,
    },
    {
        "id": "crm",
        "name": "CRM",
        "name_en": "CRM",
        "icon": "🤝",
        "category": "sales",
        "description": "Lead management, opportunities and customer relations",
        "required": False,
        "default_enabled": True,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "sectors": None,
        "aliases": [],
        "implemented": True,
    },
    {
        "id": "purchases",
        "name": "Purchases",
        "name_en": "Purchases",
        "icon": "🛒",
        "category": "operations",
        "description": "Purchase orders, receiving, and supplier management",
        "required": False,
        "default_enabled": True,
        "dependencies": ["inventory"],
        "countries": ["ES", "EC"],
        "sectors": None,
        "aliases": ["compras"],
        "implemented": True,
    },
    {
        "id": "suppliers",
        "name": "Suppliers",
        "name_en": "Suppliers",
        "icon": "🚚",
        "category": "operations",
        "description": "Supplier profiles, contacts and purchasing workflows",
        "required": False,
        "default_enabled": True,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "sectors": None,
        "aliases": ["proveedores"],
        "implemented": True,
    },
    {
        "id": "imports",
        "name": "Imports",
        "name_en": "Imports",
        "icon": "📥",
        "category": "operations",
        "description": "Bulk loading of products, customers and data via Excel/CSV",
        "required": False,
        "default_enabled": True,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "sectors": None,
        "aliases": ["importador", "importer", "importaciones"],
        "implemented": True,
    },
    {
        "id": "manufacturing",
        "name": "Manufacturing",
        "name_en": "Manufacturing",
        "icon": "🏭",
        "category": "operations",
        "description": "Production orders, BOM and manufacturing tracking",
        "required": False,
        "default_enabled": False,
        "dependencies": ["inventory"],
        "countries": ["ES", "EC"],
        "sectors": None,
        "aliases": ["productions", "production", "produccion", "producción"],
        "implemented": True,
    },
    {
        "id": "invoicing",
        "name": "Invoicing",
        "name_en": "Invoicing",
        "icon": "🧾",
        "category": "finance",
        "description": "Invoice management, credits and document numbering",
        "required": True,
        "default_enabled": True,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "sectors": None,
        "aliases": ["billing", "facturacion", "facturación"],
        "implemented": True,
    },
    {
        "id": "einvoicing",
        "name": "E-Invoicing",
        "name_en": "E-Invoicing",
        "icon": "📨",
        "category": "finance",
        "description": "Electronic submission via SRI (EC) or Facturae/SII (ES)",
        "required": False,
        "default_enabled": True,
        "dependencies": ["invoicing"],
        "countries": ["ES", "EC"],
        "sectors": None,
        "aliases": [],
        "implemented": True,
    },
    {
        "id": "finance",
        "name": "Finance",
        "name_en": "Finance",
        "icon": "💼",
        "category": "finance",
        "description": "Cash, banks and treasury operations",
        "required": False,
        "default_enabled": True,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "sectors": None,
        "aliases": ["finances", "finanzas"],
        "implemented": True,
    },
    {
        "id": "accounting",
        "name": "Accounting",
        "name_en": "Accounting",
        "icon": "📚",
        "category": "finance",
        "description": "Ledger, journal entries and accounting controls",
        "required": False,
        "default_enabled": False,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "sectors": None,
        "aliases": ["contabilidad"],
        "implemented": True,
    },
    {
        "id": "reconciliation",
        "name": "Reconciliation",
        "name_en": "Reconciliation",
        "icon": "🔄",
        "category": "finance",
        "description": "Bank statement import and reconciliation workflows",
        "required": False,
        "default_enabled": False,
        "dependencies": ["finance"],
        "countries": ["ES", "EC"],
        "sectors": None,
        "aliases": ["conciliacion", "conciliación", "conciliacionbancaria"],
        "implemented": True,
    },
    {
        "id": "expenses",
        "name": "Expenses",
        "name_en": "Expenses",
        "icon": "💸",
        "category": "finance",
        "description": "Recording and approval of expenses, mileage and per diems",
        "required": False,
        "default_enabled": True,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "sectors": None,
        "aliases": ["gastos"],
        "implemented": True,
    },
    {
        "id": "hr",
        "name": "Human Resources",
        "name_en": "Human Resources",
        "icon": "👥",
        "category": "people",
        "description": "Payroll, attendance, vacations and contracts",
        "required": False,
        "default_enabled": False,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "sectors": None,
        "aliases": ["rrhh"],
        "implemented": True,
    },
    {
        "id": "users",
        "name": "Users",
        "name_en": "Users",
        "icon": "🪪",
        "category": "people",
        "description": "Tenant users, access roles and operational permissions",
        "required": False,
        "default_enabled": False,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "sectors": None,
        "aliases": ["usuarios"],
        "implemented": True,
    },
    {
        "id": "settings",
        "name": "Settings",
        "name_en": "Settings",
        "icon": "⚙️",
        "category": "settings",
        "description": "General configuration, branding, fiscal and operations settings",
        "required": False,
        "default_enabled": False,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "sectors": None,
        "aliases": ["configuracion", "configuración"],
        "implemented": True,
    },
    {
        "id": "templates",
        "name": "Templates",
        "name_en": "Templates",
        "icon": "🧩",
        "category": "settings",
        "description": "UI templates and overlay configuration",
        "required": False,
        "default_enabled": False,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "sectors": None,
        "aliases": ["plantillas"],
        "implemented": True,
    },
    {
        "id": "notifications",
        "name": "Notifications",
        "name_en": "Notifications",
        "icon": "🔔",
        "category": "integrations",
        "description": "Notification center and alert management",
        "required": False,
        "default_enabled": False,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "sectors": None,
        "aliases": ["notificaciones"],
        "implemented": True,
    },
    {
        "id": "webhooks",
        "name": "Webhooks",
        "name_en": "Webhooks",
        "icon": "🔗",
        "category": "integrations",
        "description": "Webhook subscriptions, delivery logs and integrations",
        "required": False,
        "default_enabled": False,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "sectors": None,
        "aliases": [],
        "implemented": True,
    },
    {
        "id": "reports",
        "name": "Reports",
        "name_en": "Reports",
        "icon": "📊",
        "category": "analytics",
        "description": "Custom reports, dashboards and exports",
        "required": False,
        "default_enabled": True,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "sectors": None,
        "aliases": ["reportes"],
        "implemented": True,
    },
    {
        "id": "copilot",
        "name": "AI Copilot",
        "name_en": "AI Copilot",
        "icon": "✨",
        "category": "tools",
        "description": "AI analysis, suggestions and assisted draft creation",
        "required": False,
        "default_enabled": False,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "sectors": None,
        "aliases": [],
        "implemented": True,
    },
    {
        "id": "projects",
        "name": "Projects",
        "name_en": "Projects",
        "icon": "📋",
        "category": "operations",
        "description": "Project management, tasks and timesheets",
        "required": False,
        "default_enabled": False,
        "dependencies": [],
        "countries": ["ES", "EC"],
        "sectors": None,
        "aliases": [],
        "implemented": False,
    },
    {
        "id": "ecommerce",
        "name": "E-Commerce",
        "name_en": "E-Commerce",
        "icon": "🛍️",
        "category": "sales",
        "description": "Online stores and marketplace integrations",
        "required": False,
        "default_enabled": False,
        "dependencies": ["inventory", "sales"],
        "countries": ["ES", "EC"],
        "sectors": None,
        "aliases": [],
        "implemented": False,
    },
]


_ALL_MODULES_BY_ID: dict[str, dict[str, Any]] = {}
_ALIASES_TO_ID: dict[str, str] = {}

for entry in MODULE_REGISTRY:
    module = dict(entry)
    module_id = str(module["id"]).strip()
    aliases = {module_id, *(str(alias).strip() for alias in module.get("aliases", []))}
    module["aliases"] = sorted(alias for alias in aliases if alias)
    _ALL_MODULES_BY_ID[module_id] = module
    for alias in module["aliases"]:
        _ALIASES_TO_ID[_normalize_key(alias)] = module_id


AVAILABLE_MODULES: dict[str, dict[str, Any]] = {
    module_id: dict(module)
    for module_id, module in _ALL_MODULES_BY_ID.items()
    if bool(module.get("implemented", True))
}


def canonicalize_module_id(module_id: str | None) -> str | None:
    normalized = _normalize_key(module_id)
    if not normalized:
        return None
    return _ALIASES_TO_ID.get(normalized)


def get_module_aliases(module_id: str) -> list[str]:
    canonical = canonicalize_module_id(module_id) or str(module_id).strip().lower()
    module = _ALL_MODULES_BY_ID.get(canonical)
    if not module:
        return [canonical]
    return list(module.get("aliases", [canonical]))


def get_available_modules(
    country: str | None = None,
    sector: str | None = None,
) -> list[dict[str, Any]]:
    """Return implemented modules optionally filtered by country and sector."""
    modules = [dict(module) for module in AVAILABLE_MODULES.values()]

    if country:
        modules = [m for m in modules if country.upper() in m.get("countries", [])]

    if sector:
        modules = [
            m for m in modules if m.get("sectors") is None or sector.lower() in m.get("sectors", [])
        ]

    return modules


def get_module_by_id(module_id: str) -> dict[str, Any] | None:
    canonical = canonicalize_module_id(module_id)
    if not canonical:
        return None
    module = AVAILABLE_MODULES.get(canonical)
    return dict(module) if module else None


def get_required_modules() -> list[str]:
    return [module_id for module_id, module in AVAILABLE_MODULES.items() if module["required"]]


def get_default_enabled_modules() -> list[str]:
    return [
        module_id for module_id, module in AVAILABLE_MODULES.items() if module["default_enabled"]
    ]


def validate_module_dependencies(enabled_modules: list[str]) -> dict[str, list[str]]:
    """Validate that enabled modules have their dependencies active."""
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
