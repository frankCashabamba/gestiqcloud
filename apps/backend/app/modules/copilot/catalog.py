from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.modules.settings.application.modules_catalog import (
    canonicalize_module_id,
    get_available_modules,
)

COPILOT_TOPIC_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "id": "ventas_mes",
        "label": "Ventas por mes",
        "module_ids": ["sales", "reports"],
        "supports_ai_insights": True,
    },
    {
        "id": "ventas_por_almacen",
        "label": "Ventas por almacén",
        "module_ids": ["inventory", "sales", "reports"],
        "supports_ai_insights": True,
    },
    {
        "id": "top_productos",
        "label": "Top productos",
        "module_ids": ["products", "sales", "reports"],
        "supports_ai_insights": True,
    },
    {
        "id": "stock_bajo",
        "label": "Stock bajo",
        "module_ids": ["inventory", "purchases", "notifications"],
        "supports_ai_insights": True,
    },
    {
        "id": "pendientes_sri_sii",
        "label": "Pendientes SRI/SII",
        "module_ids": ["einvoicing", "invoicing"],
        "supports_ai_insights": True,
    },
    {
        "id": "cobros_pagos",
        "label": "Cobros y pagos",
        "module_ids": ["finance", "reconciliation", "reports"],
        "supports_ai_insights": True,
    },
    {
        "id": "pos_hoy",
        "label": "POS hoy",
        "module_ids": ["pos", "reports"],
        "supports_ai_insights": True,
    },
    {
        "id": "gastos_mes",
        "label": "Gastos por mes",
        "module_ids": ["expenses", "reports"],
        "supports_ai_insights": True,
    },
    {
        "id": "produccion_activa",
        "label": "Producción activa",
        "module_ids": ["manufacturing", "reports"],
        "supports_ai_insights": True,
    },
    {
        "id": "compras_pendientes",
        "label": "Compras pendientes",
        "module_ids": ["purchases", "suppliers"],
        "supports_ai_insights": True,
    },
    {
        "id": "prediccion_reorden",
        "label": "Predicción de reorden",
        "module_ids": ["inventory", "purchases", "notifications"],
        "supports_ai_insights": True,
    },
    {
        "id": "anomalias_ventas",
        "label": "Anomalías de ventas",
        "module_ids": ["sales", "pos", "reports"],
        "supports_ai_insights": True,
    },
    {
        "id": "clasificar_gasto",
        "label": "Clasificar gasto",
        "module_ids": ["expenses"],
        "supports_ai_insights": False,
    },
)

COPILOT_ACTION_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "id": "create_invoice_draft",
        "label": "Crear factura borrador",
        "module_ids": ["invoicing", "einvoicing"],
        "write": True,
    },
    {
        "id": "create_order_draft",
        "label": "Crear pedido borrador",
        "module_ids": ["sales", "crm"],
        "write": True,
    },
    {
        "id": "create_transfer_draft",
        "label": "Crear transferencia borrador",
        "module_ids": ["inventory"],
        "write": True,
    },
    {
        "id": "suggest_overlay_fields",
        "label": "Sugerir overlay UI",
        "module_ids": ["settings", "templates"],
        "write": False,
    },
)

CONTEXT_LOADERS: dict[str, str] = {
    "pos": "_pos",
    "inventory": "_inventory",
    "purchases": "_purchases",
    "sales": "_sales",
    "finance": "_finance",
    "manufacturing": "_manufacturing",
    "expenses": "_expenses",
    "hr": "_hr",
    "products": "_products",
    "crm": "_crm",
    "customers": "_customers",
    "suppliers": "_suppliers",
    "accounting": "_accounting",
    "invoicing": "_invoicing",
    "einvoicing": "_einvoicing",
    "reconciliation": "_reconciliation",
    "reports": "_reports",
    "notifications": "_notifications",
    "settings": "_settings",
    "users": "_users",
}


def resolve_context_module(module: str | None) -> str | None:
    canonical = canonicalize_module_id(module)
    if canonical in CONTEXT_LOADERS:
        return canonical
    return None


def default_allowed_actions() -> list[str]:
    return [entry["id"] for entry in COPILOT_ACTION_DEFINITIONS]


def get_copilot_catalog(db: Session | None = None) -> dict[str, Any]:
    available_modules = {
        module["id"]: module
        for module in get_available_modules(db=db)
        if module.get("id") in CONTEXT_LOADERS
    }

    modules = []
    for module_id in CONTEXT_LOADERS:
        module = available_modules.get(module_id)
        if not module:
            continue
        modules.append(
            {
                "id": module_id,
                "name": module.get("name", module_id),
                "icon": module.get("icon"),
                "category": module.get("category"),
                "description": module.get("description"),
                "supports_context": True,
            }
        )

    return {
        "modules": modules,
        "topics": list(COPILOT_TOPIC_DEFINITIONS),
        "actions": list(COPILOT_ACTION_DEFINITIONS),
    }
