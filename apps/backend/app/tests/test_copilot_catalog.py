from app.modules.copilot.catalog import (
    CONTEXT_LOADERS,
    default_allowed_actions,
    get_copilot_catalog,
    resolve_context_module,
)


def test_resolve_context_module_uses_global_aliases():
    assert resolve_context_module("finanzas") == "finance"
    assert resolve_context_module("produccion") == "manufacturing"
    assert resolve_context_module("inventario") == "inventory"


def test_catalog_exposes_supported_modules_only():
    catalog = get_copilot_catalog()
    module_ids = {item["id"] for item in catalog["modules"]}

    assert "inventory" in module_ids
    assert "manufacturing" in module_ids
    assert "imports" not in module_ids
    assert module_ids.issubset(set(CONTEXT_LOADERS))


def test_default_allowed_actions_match_catalog_ids():
    action_ids = {item["id"] for item in get_copilot_catalog()["actions"]}
    assert set(default_allowed_actions()) == action_ids


def test_catalog_marks_summary_topics():
    topics = get_copilot_catalog()["topics"]
    summary_ids = {item["id"] for item in topics if item.get("summary_card")}
    assert summary_ids == {"ventas_mes", "top_productos", "stock_bajo", "cobros_pagos"}
