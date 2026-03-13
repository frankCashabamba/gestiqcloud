from app.modules.settings.interface.http.public import (
    _canonical_enabled_modules,
    _production_module_enabled,
)


def test_canonical_enabled_modules_normalizes_manufacturing_aliases():
    assert _canonical_enabled_modules(["production", "Manufacturing", "producción"]) == [
        "manufacturing"
    ]


def test_production_module_enabled_accepts_manufacturing_aliases():
    assert _production_module_enabled(["manufacturing"]) is True
    assert _production_module_enabled(["production"]) is True
    assert _production_module_enabled(["produccion"]) is True
    assert _production_module_enabled(["inventory"]) is False
