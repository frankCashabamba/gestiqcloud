"""Catálogo de Módulos Disponibles del Sistema"""

from typing import Any

AVAILABLE_MODULES: list[dict[str, Any]] = [
    {
        "id": "pos",
        "name": "Punto de Venta",
        "name_en": "Point of Sale",
        "icon": "💰",
        "category": "sales",
        "description": "Sistema TPV con tickets, facturación rápida e impresión térmica",
        "required": False,
        "default_enabled": True,
        "dependencies": ["inventory", "invoicing"],
        "countries": ["ES", "EC"],
    },
    {
        "id": "inventory",
        "name": "Inventario",
        "name_en": "Inventory",
        "icon": "📦",
        "category": "operations",
        "description": "Control de stock, almacenes, lotes y caducidades",
        "required": False,
        "default_enabled": True,
        "dependencies": [],
        "countries": ["ES", "EC"],
    },
    {
        "id": "invoicing",
        "name": "Facturación",
        "name_en": "Invoicing",
        "icon": "🧾",
        "category": "finance",
        "description": "Gestión de facturas, abonos y numeración documental",
        "required": True,
        "default_enabled": True,
        "dependencies": [],
        "countries": ["ES", "EC"],
    },
    {
        "id": "einvoicing",
        "name": "Facturación Electrónica",
        "name_en": "E-Invoicing",
        "icon": "📨",
        "category": "finance",
        "description": "Envío electrónico SRI (EC) o Facturae/SII (ES)",
        "required": False,
        "default_enabled": True,
        "dependencies": ["invoicing"],
        "countries": ["ES", "EC"],
    },
    {
        "id": "purchases",
        "name": "Compras",
        "name_en": "Purchases",
        "icon": "🛒",
        "category": "operations",
        "description": "Órdenes de compra, recepción y gestión de proveedores",
        "required": False,
        "default_enabled": True,
        "dependencies": ["inventory"],
        "countries": ["ES", "EC"],
    },
    {
        "id": "expenses",
        "name": "Gastos",
        "name_en": "Expenses",
        "icon": "💸",
        "category": "finance",
        "description": "Registro y aprobación de gastos, kilometrajes y dietas",
        "required": False,
        "default_enabled": True,
        "dependencies": [],
        "countries": ["ES", "EC"],
    },
    {
        "id": "finance",
        "name": "Finanzas",
        "name_en": "Finance",
        "icon": "💼",
        "category": "finance",
        "description": "Plan contable, conciliación bancaria y reportes fiscales",
        "required": True,
        "default_enabled": True,
        "dependencies": ["invoicing"],
        "countries": ["ES", "EC"],
    },
    {
        "id": "hr",
        "name": "Recursos Humanos",
        "name_en": "Human Resources",
        "icon": "👥",
        "category": "people",
        "description": "Nómina, asistencia, vacaciones y contratos",
        "required": False,
        "default_enabled": False,
        "dependencies": [],
        "countries": ["ES", "EC"],
    },
    {
        "id": "sales",
        "name": "Ventas",
        "name_en": "Sales",
        "icon": "📈",
        "category": "sales",
        "description": "Presupuestos, pedidos, albaranes y seguimiento comercial",
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
        "description": "Gestión de leads, oportunidades y relación con clientes",
        "required": False,
        "default_enabled": True,
        "dependencies": [],
        "countries": ["ES", "EC"],
    },
    {
        "id": "imports",
        "name": "Importaciones",
        "name_en": "Imports",
        "icon": "📥",
        "category": "operations",
        "description": "Carga masiva de productos, clientes y datos via Excel/CSV",
        "required": False,
        "default_enabled": True,
        "dependencies": [],
        "countries": ["ES", "EC"],
    },
    {
        "id": "reports",
        "name": "Reportes",
        "name_en": "Reports",
        "icon": "📊",
        "category": "analytics",
        "description": "Informes personalizados, dashboards y exportación",
        "required": False,
        "default_enabled": True,
        "dependencies": [],
        "countries": ["ES", "EC"],
    },
    {
        "id": "manufacturing",
        "name": "Fabricación",
        "name_en": "Manufacturing",
        "icon": "🏭",
        "category": "operations",
        "description": "Órdenes de producción, BOM y seguimiento de fabricación",
        "required": False,
        "default_enabled": False,
        "dependencies": ["inventory"],
        "countries": ["ES", "EC"],
    },
    {
        "id": "projects",
        "name": "Proyectos",
        "name_en": "Projects",
        "icon": "📋",
        "category": "operations",
        "description": "Gestión de proyectos, tareas y timesheet",
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
        "description": "Integración con tiendas online y marketplaces",
        "required": False,
        "default_enabled": False,
        "dependencies": ["inventory", "sales"],
        "countries": ["ES", "EC"],
    },
]

# Categorías de módulos
MODULE_CATEGORIES = [
    {"id": "sales", "name": "Ventas", "icon": "🛍️", "order": 1},
    {"id": "finance", "name": "Finanzas", "icon": "💰", "order": 2},
    {"id": "operations", "name": "Operaciones", "icon": "⚙️", "order": 3},
    {"id": "people", "name": "Personas", "icon": "👥", "order": 4},
    {"id": "analytics", "name": "Análisis", "icon": "📊", "order": 5},
]


def get_available_modules(country: str = None) -> list[dict[str, Any]]:
    """Obtener módulos disponibles, opcionalmente filtrados por país"""
    if country:
        return [m for m in AVAILABLE_MODULES if country.upper() in m["countries"]]
    return AVAILABLE_MODULES.copy()


def get_module_by_id(module_id: str) -> dict[str, Any] | None:
    """Obtener módulo por ID"""
    return next((m for m in AVAILABLE_MODULES if m["id"] == module_id), None)


def get_required_modules() -> list[str]:
    """Obtener lista de módulos obligatorios"""
    return [m["id"] for m in AVAILABLE_MODULES if m["required"]]


def get_default_enabled_modules() -> list[str]:
    """Obtener lista de módulos habilitados por defecto"""
    return [m["id"] for m in AVAILABLE_MODULES if m["default_enabled"]]


def validate_module_dependencies(enabled_modules: list[str]) -> dict[str, list[str]]:
    """
    Validar que los módulos habilitados tengan sus dependencias activas

    Returns:
        Dict con módulos y sus dependencias faltantes
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
