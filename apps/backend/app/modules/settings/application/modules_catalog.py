"""Catalog of Available System Modules"""

from typing import Any

AVAILABLE_MODULES: list[dict[str, Any]] = [
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
        "sectors": None,  # Available for all sectors
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
        "sectors": None,  # Available for all sectors
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
        "sectors": ["retail"],  # Only available for retail sector
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
    },
    {
        "id": "finance",
        "name": "Finance",
        "name_en": "Finance",
        "icon": "💼",
        "category": "finance",
        "description": "Chart of accounts, bank reconciliation and tax reporting",
        "required": True,
        "default_enabled": True,
        "dependencies": ["invoicing"],
        "countries": ["ES", "EC"],
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
    },
    {
        "id": "projects",
        "name": "Projects",
        "name_en": "Projects",
        "icon": "📋",
        "category": "operations",
        "description": "Project management, tasks and timesheet",
        "required": False,
        "default_enabled": False,
        "dependencies": [],
        "countries": ["ES", "EC"],
    },
    {
        "id": "ecommerce",
        "name": "E-Commerce",
        "name_en": "E-Commerce",
        "icon": "🛍️",
        "category": "sales",
        "description": "Integration with online stores and marketplaces",
        "required": False,
        "default_enabled": False,
        "dependencies": ["inventory", "sales"],
        "countries": ["ES", "EC"],
    },
]

# Module categories
MODULE_CATEGORIES = [
    {"id": "sales", "name": "Sales", "icon": "🛍️", "order": 1},
    {"id": "finance", "name": "Finance", "icon": "💰", "order": 2},
    {"id": "operations", "name": "Operations", "icon": "⚙️", "order": 3},
    {"id": "people", "name": "People", "icon": "👥", "order": 4},
    {"id": "analytics", "name": "Analytics", "icon": "📊", "order": 5},
]


def get_available_modules(country: str = None, sector: str = None) -> list[dict[str, Any]]:
    """
    Get available modules, optionally filtered by country and sector.

    Args:
        country: ISO code to filter by country (e.g., 'ES', 'EC')
        sector: Sector code to filter by (e.g., 'retail', 'bakery', 'workshop')

    Returns:
        List of available modules for the given filters
    """
    modules = AVAILABLE_MODULES.copy()

    # Filter by country
    if country:
        modules = [m for m in modules if country.upper() in m.get("countries", [])]

    # Filter by sector
    if sector:
        modules = [
            m for m in modules if m.get("sectors") is None or sector.lower() in m.get("sectors", [])
        ]

    return modules


def get_module_by_id(module_id: str) -> dict[str, Any] | None:
    """Get module by ID"""
    return next((m for m in AVAILABLE_MODULES if m["id"] == module_id), None)


def get_required_modules() -> list[str]:
    """Get list of required modules"""
    return [m["id"] for m in AVAILABLE_MODULES if m["required"]]


def get_default_enabled_modules() -> list[str]:
    """Get list of modules enabled by default"""
    return [m["id"] for m in AVAILABLE_MODULES if m["default_enabled"]]


def validate_module_dependencies(enabled_modules: list[str]) -> dict[str, list[str]]:
    """
    Validate that enabled modules have their dependencies active

    Returns:
        Dict with modules and their missing dependencies
    """
    missing_deps: dict[str, list[str]] = {}

    for module_id in enabled_modules:
        module = get_module_by_id(module_id)
        if not module:
            continue

        for dep in module.get("dependencies", []):
            if dep not in enabled_modules:
                if module_id not in missing_deps:
                    missing_deps[module_id] = []
                missing_deps[module_id].append(dep)

    return missing_deps
