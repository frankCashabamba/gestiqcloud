from app.modules.settings.interface.http.public import (
    _canonical_enabled_modules,
    _production_module_enabled,
)


def test_canonical_enabled_modules_normalizes_case():
    assert _canonical_enabled_modules(["manufacturing", "Manufacturing"]) == ["manufacturing"]


def test_production_module_enabled():
    assert _production_module_enabled(["manufacturing"]) is True
    assert _production_module_enabled(["inventory"]) is False
