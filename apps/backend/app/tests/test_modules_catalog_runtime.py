import pytest

from app.models.core.module import Module
from app.modules.settings.application.modules_catalog import (
    get_available_modules,
    is_standalone_module,
    resolve_module_parent,
)

pytestmark = pytest.mark.no_db


def test_available_modules_use_db_overrides(db):
    db.add(
        Module(
            name="Inventario Pro",
            description="Inventario con branding",
            active=True,
            icon="📚",
            url="inventory",
            initial_template="inventory",
            context_type="none",
            context_filters={"catalog_id": "inventory", "default_enabled": True},
            category="custom-ops",
        )
    )
    db.commit()

    modules = get_available_modules(db=db)
    inventory = next(item for item in modules if item["id"] == "inventory")

    assert inventory["name"] == "Inventario Pro"
    assert inventory["category"] == "custom-ops"
    assert inventory["icon"] == "📚"
    assert inventory["default_enabled"] is True


def test_available_modules_hide_db_overridden_inactive_module(db):
    db.add(
        Module(
            name="Reportes ocultos",
            description="Oculto por admin",
            active=False,
            icon="📉",
            url="reports",
            initial_template="reports",
            context_type="none",
            context_filters={"catalog_id": "reports"},
            category="analytics",
        )
    )
    db.commit()

    modules = get_available_modules(db=db, sector="retail")
    module_ids = {item["id"] for item in modules}

    assert "reports" not in module_ids


def test_available_modules_expose_runtime_navigation_metadata(db):
    modules = get_available_modules(db=db)
    settings = next(item for item in modules if item["id"] == "settings")
    reconciliation = next(item for item in modules if item["id"] == "reconciliation")

    assert settings["nav_group"] == "user_menu"
    assert settings["contractable"] is False
    assert settings["use_module_loader"] is False
    assert reconciliation["nav_group"] == "hidden"
    assert reconciliation["contractable"] is False


def test_settings_child_modules_are_not_standalone():
    assert resolve_module_parent("users") == "settings"
    assert resolve_module_parent("templates") == "settings"
    assert resolve_module_parent("webhooks") == "settings"
    assert resolve_module_parent("notifications") == "settings"
    assert resolve_module_parent("einvoicing") == "settings"
    assert resolve_module_parent("reconciliation") == "settings"
    assert is_standalone_module("settings") is True
    assert is_standalone_module("users") is False
