import pytest

from app.models.core.module import Module
from app.modules.settings.application.modules_catalog import get_available_modules

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
