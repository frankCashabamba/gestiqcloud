"""Tests for utils/unit_converter.py — pure functions, no DB needed."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.utils.unit_converter import (
    UnitType,
    are_compatible_units,
    convert,
    convert_temperature,
    convert_volume,
    convert_weight,
    format_qty,
    get_unit_type,
    is_valid_unit,
    normalize_to_base,
    normalize_unit_name,
)

# ── get_unit_type ─────────────────────────────────────────────────────────────


def test_get_unit_type_weight():
    assert get_unit_type("kg") == UnitType.WEIGHT
    assert get_unit_type("g") == UnitType.WEIGHT
    assert get_unit_type("lb") == UnitType.WEIGHT
    assert get_unit_type("oz") == UnitType.WEIGHT
    assert get_unit_type("ton") == UnitType.WEIGHT
    assert get_unit_type("mg") == UnitType.WEIGHT


def test_get_unit_type_volume():
    assert get_unit_type("L") == UnitType.VOLUME
    assert get_unit_type("ml") == UnitType.VOLUME
    assert get_unit_type("gal") == UnitType.VOLUME
    assert get_unit_type("cup") == UnitType.VOLUME


def test_get_unit_type_temperature():
    assert get_unit_type("C") == UnitType.TEMPERATURE
    assert get_unit_type("F") == UnitType.TEMPERATURE
    assert get_unit_type("K") == UnitType.TEMPERATURE
    assert get_unit_type("celsius") == UnitType.TEMPERATURE
    assert get_unit_type("fahrenheit") == UnitType.TEMPERATURE


def test_get_unit_type_count():
    assert get_unit_type("uds") == UnitType.COUNT
    assert get_unit_type("pcs") == UnitType.COUNT
    assert get_unit_type("un") == UnitType.COUNT
    assert get_unit_type("unit") == UnitType.COUNT
    assert get_unit_type("units") == UnitType.COUNT


def test_get_unit_type_unknown():
    assert get_unit_type("xyz") is None
    assert get_unit_type("") is None


# ── normalize_unit_name ───────────────────────────────────────────────────────


def test_normalize_unit_name_spanish_weight():
    assert normalize_unit_name("kilogramo") == "kg"
    assert normalize_unit_name("kilogramos") == "kg"
    assert normalize_unit_name("gramo") == "g"
    assert normalize_unit_name("gramos") == "g"
    assert normalize_unit_name("libra") == "lb"
    assert normalize_unit_name("onza") == "oz"


def test_normalize_unit_name_spanish_volume():
    assert normalize_unit_name("litro") == "L"
    assert normalize_unit_name("litros") == "L"
    assert normalize_unit_name("mililitro") == "ml"
    assert normalize_unit_name("galon") == "gal"


def test_normalize_unit_name_count():
    assert normalize_unit_name("unidad") == "uds"
    assert normalize_unit_name("pieza") == "uds"
    assert normalize_unit_name("piezas") == "uds"


def test_normalize_unit_name_temperature():
    assert normalize_unit_name("celsius") == "C"
    assert normalize_unit_name("fahrenheit") == "F"
    assert normalize_unit_name("kelvin") == "K"


def test_normalize_unit_name_passthrough_unknown():
    assert normalize_unit_name("kg") == "kg"
    assert normalize_unit_name("xyz") == "xyz"


# ── convert_weight ────────────────────────────────────────────────────────────


def test_convert_weight_kg_to_g():
    result = convert_weight(Decimal("1"), "kg", "g")
    assert float(result) == pytest.approx(1000.0)


def test_convert_weight_lb_to_kg():
    result = convert_weight(Decimal("1"), "lb", "kg")
    assert float(result) == pytest.approx(0.453592, rel=1e-4)


def test_convert_weight_g_to_kg():
    result = convert_weight(Decimal("500"), "g", "kg")
    assert float(result) == pytest.approx(0.5)


def test_convert_weight_same_unit():
    result = convert_weight(Decimal("5"), "kg", "kg")
    assert float(result) == pytest.approx(5.0)


def test_convert_weight_invalid_from_unit_raises():
    with pytest.raises(ValueError, match="desconocida"):
        convert_weight(Decimal("1"), "xyz", "kg")


def test_convert_weight_invalid_to_unit_raises():
    with pytest.raises(ValueError, match="desconocida"):
        convert_weight(Decimal("1"), "kg", "xyz")


# ── convert_volume ────────────────────────────────────────────────────────────


def test_convert_volume_L_to_ml():
    result = convert_volume(Decimal("1"), "L", "ml")
    assert float(result) == pytest.approx(1000.0)


def test_convert_volume_gal_to_L():
    result = convert_volume(Decimal("1"), "gal", "L")
    assert float(result) == pytest.approx(3.78541, rel=1e-4)


def test_convert_volume_invalid_from_unit_raises():
    with pytest.raises(ValueError, match="desconocida"):
        convert_volume(Decimal("1"), "xyz", "L")


def test_convert_volume_invalid_to_unit_raises():
    with pytest.raises(ValueError, match="desconocida"):
        convert_volume(Decimal("1"), "L", "xyz")


# ── convert_temperature ───────────────────────────────────────────────────────


def test_convert_temperature_C_to_F():
    result = convert_temperature(Decimal("0"), "C", "F")
    assert float(result) == pytest.approx(32.0)


def test_convert_temperature_F_to_C():
    result = convert_temperature(Decimal("32"), "F", "C")
    assert float(result) == pytest.approx(0.0)


def test_convert_temperature_C_to_K():
    result = convert_temperature(Decimal("0"), "C", "K")
    assert float(result) == pytest.approx(273.15)


def test_convert_temperature_K_to_C():
    result = convert_temperature(Decimal("273.15"), "K", "C")
    assert float(result) == pytest.approx(0.0, abs=1e-6)


def test_convert_temperature_C_to_C():
    result = convert_temperature(Decimal("100"), "C", "C")
    assert float(result) == pytest.approx(100.0)


def test_convert_temperature_invalid_from_raises():
    with pytest.raises(ValueError, match="desconocida"):
        convert_temperature(Decimal("100"), "X", "C")


def test_convert_temperature_invalid_to_raises():
    with pytest.raises(ValueError, match="desconocida"):
        convert_temperature(Decimal("100"), "C", "X")


# ── convert (main function) ───────────────────────────────────────────────────


def test_convert_weight():
    assert convert(1, "kg", "g") == pytest.approx(1000.0)


def test_convert_volume():
    assert convert(1, "L", "ml") == pytest.approx(1000.0)


def test_convert_temperature():
    assert convert(100, "C", "F") == pytest.approx(212.0)


def test_convert_count_same_unit():
    assert convert(5, "uds", "uds") == pytest.approx(5.0)


def test_convert_same_unit_returns_same():
    assert convert(3.5, "kg", "kg") == pytest.approx(3.5)


def test_convert_unknown_from_unit_raises():
    with pytest.raises(ValueError, match="desconocida"):
        convert(1, "xyz", "kg")


def test_convert_unknown_to_unit_raises():
    with pytest.raises(ValueError, match="desconocida"):
        convert(1, "kg", "xyz")


def test_convert_incompatible_units_raises():
    with pytest.raises(ValueError, match="No se puede convertir"):
        convert(1, "kg", "L")


def test_convert_using_standard_short_names():
    # Standard short names work directly
    assert convert(1, "kg", "g") == pytest.approx(1000.0)
    assert convert(1, "L", "ml") == pytest.approx(1000.0)


# ── normalize_to_base ─────────────────────────────────────────────────────────


def test_normalize_to_base_weight():
    qty, unit = normalize_to_base(1000, "g")
    assert qty == pytest.approx(1.0)
    assert unit == "kg"


def test_normalize_to_base_volume():
    qty, unit = normalize_to_base(1000, "ml")
    assert qty == pytest.approx(1.0)
    assert unit == "L"


def test_normalize_to_base_temperature():
    qty, unit = normalize_to_base(32, "F")
    assert qty == pytest.approx(0.0)
    assert unit == "C"


def test_normalize_to_base_count():
    qty, unit = normalize_to_base(5, "pcs")
    assert qty == 5
    assert unit == "uds"


def test_normalize_to_base_unknown_raises():
    with pytest.raises(ValueError, match="desconocida"):
        normalize_to_base(1, "xyz")


# ── format_qty ────────────────────────────────────────────────────────────────


def test_format_qty_default_decimals():
    result = format_qty(22.6796, "kg")
    assert result == "22.68 kg"


def test_format_qty_zero_decimals():
    result = format_qty(22.6796, "kg", decimals=0)
    assert result == "23 kg"


def test_format_qty_custom_decimals():
    result = format_qty(3.78541, "L", decimals=4)
    assert result == "3.7854 L"


# ── is_valid_unit ─────────────────────────────────────────────────────────────


def test_is_valid_unit_known():
    assert is_valid_unit("kg") is True
    assert is_valid_unit("L") is True
    assert is_valid_unit("C") is True
    assert is_valid_unit("pcs") is True


def test_is_valid_unit_unknown():
    assert is_valid_unit("xyz") is False
    assert is_valid_unit("") is False


# ── are_compatible_units ──────────────────────────────────────────────────────


def test_are_compatible_units_same_type():
    assert are_compatible_units("kg", "g") is True
    assert are_compatible_units("L", "ml") is True
    assert are_compatible_units("C", "F") is True


def test_are_compatible_units_different_types():
    assert are_compatible_units("kg", "L") is False
    assert are_compatible_units("kg", "C") is False


def test_are_compatible_units_unknown():
    assert are_compatible_units("xyz", "kg") is False
    assert are_compatible_units("kg", "xyz") is False
