"""Tests de regresión para product_matching.py.

Cubre los bugs históricos reportados:
- _parse_numeric: símbolo de moneda delante ("$ 0.0034" → 0.0)
- _parse_numeric: miles con coma y sufijo de unidad ("60,000 ml" → error de conversión)
"""

from __future__ import annotations

import pytest

from app.modules.importador.services.product_matching import (
    _infer_pack_conversion_factor,
    _norm_import_text,
    _parse_numeric,
    _score_product_candidate,
    _strip_pack_tokens,
)

# ── _parse_numeric ─────────────────────────────────────────────────────────


class TestParseNumeric:
    """Regresión completa de _parse_numeric."""

    # Casos vacíos / nulos
    def test_none_returns_zero(self):
        assert _parse_numeric(None) == 0.0

    def test_empty_string_returns_zero(self):
        assert _parse_numeric("") == 0.0

    def test_zero_int(self):
        assert _parse_numeric(0) == 0.0

    # Valores simples
    def test_integer_string(self):
        assert _parse_numeric("42") == 42.0

    def test_float_string(self):
        assert _parse_numeric("3.14") == 3.14

    def test_numeric_int(self):
        assert _parse_numeric(100) == 100.0

    def test_numeric_float(self):
        assert _parse_numeric(1.5) == 1.5

    # ── Bug #1: símbolo de moneda delante ──────────────────────────────────
    def test_dollar_prefix_small_price(self):
        """Regresión: '$ 0.0034' devolvía 0.0 porque el regex no toleraba '$'."""
        assert _parse_numeric("$ 0.0034") == pytest.approx(0.0034)

    def test_dollar_prefix_no_space(self):
        assert _parse_numeric("$1.50") == pytest.approx(1.5)

    def test_euro_prefix(self):
        assert _parse_numeric("€ 12.99") == pytest.approx(12.99)

    def test_sol_prefix(self):
        assert _parse_numeric("S/ 45.00") == pytest.approx(45.0)

    def test_currency_prefix_with_thousands(self):
        assert _parse_numeric("$ 1,234.56") == pytest.approx(1234.56)

    # ── Bug #2: miles con coma + sufijo de unidad ──────────────────────────
    def test_comma_thousands_with_unit_suffix(self):
        """Regresión: '60,000 ml' fallaba la conversión a float."""
        assert _parse_numeric("60,000 ml") == pytest.approx(60000.0)

    def test_comma_thousands_no_suffix(self):
        assert _parse_numeric("60,000") == pytest.approx(60000.0)

    def test_comma_thousands_large(self):
        assert _parse_numeric("1,200,000") == pytest.approx(1200000.0)

    # Formato anglosajón (coma = miles, punto = decimal)
    def test_anglosaxon_format(self):
        assert _parse_numeric("1,234.56") == pytest.approx(1234.56)

    def test_anglosaxon_no_decimals(self):
        assert _parse_numeric("1,500") == pytest.approx(1500.0)

    # Formato europeo (punto = miles, coma = decimal)
    def test_european_format(self):
        assert _parse_numeric("1.234,56") == pytest.approx(1234.56)

    def test_european_no_thousands(self):
        assert _parse_numeric("99,50") == pytest.approx(99.5)

    # Espacios como separador de miles
    def test_space_as_thousands_separator(self):
        assert _parse_numeric("1 234") == pytest.approx(1234.0)

    # Sufijos de unidad sin miles
    def test_simple_value_with_unit_suffix(self):
        assert _parse_numeric("5 kg") == pytest.approx(5.0)

    def test_decimal_with_unit_suffix(self):
        assert _parse_numeric("0.500 kg") == pytest.approx(0.5)

    # Valores que no pueden parsearse
    def test_pure_text_returns_zero(self):
        assert _parse_numeric("no hay número") == 0.0

    def test_only_symbols_returns_zero(self):
        assert _parse_numeric("$€") == 0.0


# ── _norm_import_text ──────────────────────────────────────────────────────


class TestNormImportText:
    def test_strips_accents(self):
        assert _norm_import_text("Azúcar") == "azucar"

    def test_lowercases(self):
        assert _norm_import_text("LECHE ENTERA") == "leche entera"

    def test_collapses_spaces(self):
        assert _norm_import_text("  sal    fina  ") == "sal fina"

    def test_removes_special_chars(self):
        assert _norm_import_text("aceite-de-oliva!") == "aceite de oliva"


# ── _strip_pack_tokens ────────────────────────────────────────────────────


class TestStripPackTokens:
    def test_removes_kg(self):
        result = _strip_pack_tokens("Harina 50kg")
        assert "kg" not in result
        assert "harina" in result

    def test_removes_ml(self):
        result = _strip_pack_tokens("Aceite 1000ml")
        assert "ml" not in result

    def test_removes_litros(self):
        result = _strip_pack_tokens("Leche 1L")
        assert "leche" in result

    def test_preserves_product_name(self):
        result = _strip_pack_tokens("Sal 1kg bolsa")
        assert "sal" in result
        assert "bolsa" in result


# ── _infer_pack_conversion_factor ─────────────────────────────────────────


class TestInferPackConversionFactor:
    def test_returns_1_for_uds_unit(self):
        assert _infer_pack_conversion_factor("Galletas 24 unidades", "uds") == 1.0

    def test_returns_1_when_no_match(self):
        assert _infer_pack_conversion_factor("Aceite extra virgen", "ml") == 1.0

    def test_extracts_ml_quantity(self):
        factor = _infer_pack_conversion_factor("Bebida gaseosa 500ml", "ml")
        assert factor == pytest.approx(500.0)

    def test_extracts_kg_quantity(self):
        factor = _infer_pack_conversion_factor("Harina de trigo 2kg", "kg")
        assert factor == pytest.approx(2.0)


# ── _score_product_candidate ──────────────────────────────────────────────


class TestScoreProductCandidate:
    """Tests básicos de scoring — sin base de datos, usando objetos simples."""

    class _FakeProduct:
        def __init__(self, name, unit="uds", import_aliases=None, product_metadata=None):
            self.name = name
            self.unit = unit
            self.import_aliases = import_aliases or []
            self.product_metadata = product_metadata or {}

    def test_exact_name_match_scores_high(self):
        product = self._FakeProduct("Azucar Blanca")
        score, reason, _ = _score_product_candidate("Azucar Blanca", product)
        assert score >= 0.90
        assert reason in ("name_exact", "alias_exact", "alias")

    def test_unrelated_name_scores_low(self):
        product = self._FakeProduct("Papel Higiénico")
        score, _, _ = _score_product_candidate("Aceite de Oliva", product)
        assert score < 0.80

    def test_empty_description_scores_zero(self):
        product = self._FakeProduct("Sal")
        score, reason, _ = _score_product_candidate("", product)
        assert score == 0.0
        assert reason is None

    def test_alias_exact_match_scores_099(self):
        product = self._FakeProduct(
            "Harina",
            import_aliases=[{"name": "harina de trigo", "factor": 1.0}],
        )
        score, reason, _ = _score_product_candidate("Harina de Trigo", product)
        assert score == pytest.approx(0.99)
        assert reason == "alias_exact"
