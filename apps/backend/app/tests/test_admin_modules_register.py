import pytest

from app.models.core.module import Module
from app.modules.modules_catalog.interface.http.admin import register_modules

pytestmark = pytest.mark.no_db


def test_register_modules_falls_back_to_backend_catalog(db):
    data = register_modules({"dir": "Z:/missing/modules"}, db)

    assert data["source"] == "backend_catalog"
    assert "registrados" not in data
    assert "ya_existentes" not in data
    assert "ignorados" not in data
    assert "warnings" in data
    assert "inventory" in (data["registered"] + data["already_existing"])

    inventory = db.query(Module).filter(Module.name == "inventory").first()
    assert inventory is not None
    assert inventory.initial_template == "inventory"
    assert (inventory.context_filters or {}).get("catalog_id") == "inventory"


def test_register_modules_does_not_duplicate_catalog_entries(db):
    payload = {"dir": "Z:/missing/modules"}

    first = register_modules(payload, db)
    assert first["source"] == "backend_catalog"

    data = register_modules(payload, db)

    assert data["registered"] == []
    assert "inventory" in data["already_existing"]
    assert db.query(Module).filter(Module.name == "inventory").count() == 1


def test_register_modules_uses_complete_canonical_catalog(db):
    data = register_modules({"dir": "Z:/missing/modules"}, db)

    assert data["source"] == "backend_catalog"
    names = {row.name for row in db.query(Module).all()}

    assert "imports" in names
    assert "settings" in names
    assert "products" in names
    assert "suppliers" in names
    assert "reconciliation" in names
    assert "webhooks" in names
    assert "ecommerce" not in names
    assert "projects" not in names


def test_register_modules_upserts_legacy_alias_to_canonical_name(db):
    legacy = Module(
        name="importador",
        description="Legacy importer",
        active=False,
        initial_template="Panel",
        context_type="none",
    )
    db.add(legacy)
    db.commit()
    db.refresh(legacy)

    data = register_modules({"dir": "Z:/missing/modules", "upsert": True}, db)

    refreshed = db.query(Module).filter(Module.id == legacy.id).first()
    assert refreshed is not None
    assert refreshed.name == "imports"
    assert refreshed.active is True
    assert db.query(Module).filter(Module.name == "imports").count() == 1
    assert "imports" in data["updated"]
