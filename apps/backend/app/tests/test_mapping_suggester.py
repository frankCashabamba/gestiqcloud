"""Tests for AI-powered mapping suggester."""

import pytest

from app.modules.imports.ai.mapping_suggester import (
    MappingSuggester,
    MappingSuggestion,
    mapping_suggester,
)


class TestMappingSuggester:
    """Tests for MappingSuggester class."""

    def test_suggest_with_heuristics_products(self):
        """Test heuristic mapping for product headers."""
        suggester = MappingSuggester()

        headers = ["Nombre", "Precio", "Cantidad", "Categoría", "SKU"]
        result = suggester._suggest_with_heuristics(headers, "products")

        assert isinstance(result, MappingSuggestion)
        assert result.provider == "heuristics"
        assert result.confidence > 0

        assert "Nombre" in result.mappings
        assert result.mappings["Nombre"] == "name"

        assert "Precio" in result.mappings
        assert result.mappings["Precio"] == "price"

        assert "Cantidad" in result.mappings
        assert result.mappings["Cantidad"] == "stock"

    def test_suggest_with_heuristics_bank(self):
        """Test heuristic mapping for bank transaction headers."""
        suggester = MappingSuggester()

        headers = ["Fecha", "Importe", "Concepto", "Saldo", "IBAN"]
        result = suggester._suggest_with_heuristics(headers, "bank_transactions")

        assert result.provider == "heuristics"

        assert "Fecha" in result.mappings
        assert result.mappings["Fecha"] == "value_date"

        assert "Importe" in result.mappings
        assert result.mappings["Importe"] == "amount"

        assert "Concepto" in result.mappings
        assert result.mappings["Concepto"] == "narrative"

    def test_suggest_with_heuristics_invoices(self):
        """Test heuristic mapping for invoice headers."""
        suggester = MappingSuggester()

        headers = ["Numero Factura", "Fecha", "Proveedor", "Subtotal", "IVA", "Total"]
        result = suggester._suggest_with_heuristics(headers, "invoices")

        assert "Total" in result.mappings
        assert result.mappings["Total"] == "total"

        assert "IVA" in result.mappings
        assert result.mappings["IVA"] == "tax"

    def test_suggest_with_heuristics_english_headers(self):
        """Test heuristic mapping with English headers."""
        suggester = MappingSuggester()

        headers = ["Product Name", "Price", "Stock", "Category", "SKU"]
        result = suggester._suggest_with_heuristics(headers, "products")

        assert "Price" in result.mappings
        assert result.mappings["Price"] == "price"

        assert "Stock" in result.mappings
        assert result.mappings["Stock"] == "stock"

    def test_suggest_with_transforms(self):
        """Test that date/number fields get appropriate transforms."""
        suggester = MappingSuggester()

        headers = ["Fecha", "Precio", "Nombre"]
        result = suggester._suggest_with_heuristics(headers, "bank_transactions")

        assert result.transforms is not None
        if "Fecha" in result.mappings:
            assert "Fecha" in result.transforms
            assert result.transforms["Fecha"] == "parse_date"

    def test_cache_key_generation(self):
        """Test cache key is deterministic."""
        suggester = MappingSuggester()

        headers = ["A", "B", "C"]
        key1 = suggester._get_cache_key(headers, "products", "tenant1")
        key2 = suggester._get_cache_key(headers, "products", "tenant1")
        key3 = suggester._get_cache_key(headers, "products", "tenant2")
        key4 = suggester._get_cache_key(["C", "A", "B"], "products", "tenant1")

        assert key1 == key2
        assert key1 != key3
        assert key1 == key4

    def test_empty_headers(self):
        """Test with empty headers list."""
        suggester = MappingSuggester()

        result = suggester._suggest_with_heuristics([], "products")

        assert result.mappings == {}
        assert result.confidence == 0.0

    def test_no_matches(self):
        """Test with headers that don't match any patterns."""
        suggester = MappingSuggester()

        headers = ["XYZ123", "ABC456", "Unknown_Field"]
        result = suggester._suggest_with_heuristics(headers, "products")

        assert len(result.mappings) == 0
        assert result.confidence == 0.0

    def test_partial_matches(self):
        """Test with some matching and some non-matching headers."""
        suggester = MappingSuggester()

        headers = ["Nombre", "XYZ123", "Precio", "Unknown"]
        result = suggester._suggest_with_heuristics(headers, "products")

        assert len(result.mappings) == 2
        assert "Nombre" in result.mappings
        assert "Precio" in result.mappings
        assert "XYZ123" not in result.mappings

    def test_format_sample_rows(self):
        """Test sample row formatting for prompts."""
        suggester = MappingSuggester()

        headers = ["Name", "Price"]
        rows = [["Product A", 10.50], ["Product B", 20.00]]

        formatted = suggester._format_sample_rows(headers, rows)

        assert "Sample data" in formatted
        assert "Row 1" in formatted
        assert "Product A" in formatted

    def test_format_sample_rows_empty(self):
        """Test formatting with no rows."""
        suggester = MappingSuggester()

        result = suggester._format_sample_rows(["A", "B"], [])
        assert result == ""


@pytest.mark.asyncio
class TestMappingSuggesterAsync:
    """Async tests for MappingSuggester."""

    async def test_suggest_mapping_uses_cache(self):
        """Test that repeated calls use cache."""
        suggester = MappingSuggester()
        suggester.clear_cache()

        headers = ["TestHeader1", "TestHeader2", "TestHeader3"]

        await suggester.suggest_mapping(
            headers=headers, doc_type="products", tenant_id="test_cache_tenant", use_ai=False
        )
        result2 = await suggester.suggest_mapping(
            headers=headers, doc_type="products", tenant_id="test_cache_tenant", use_ai=False
        )

        assert result2.from_cache is True
        suggester.clear_cache("test_cache_tenant")

    async def test_suggest_mapping_fallback_to_heuristics(self):
        """Test fallback to heuristics when AI is disabled."""
        suggester = MappingSuggester()

        headers = ["Producto", "Valor", "Cantidad"]
        result = await suggester.suggest_mapping(headers=headers, doc_type="products", use_ai=False)

        assert result.provider == "heuristics"
        assert "Producto" in result.mappings
        assert result.mappings["Producto"] == "name"

    async def test_clear_cache(self):
        """Test cache clearing."""
        suggester = MappingSuggester()

        await suggester.suggest_mapping(
            headers=["A", "B"], doc_type="products", tenant_id="t1", use_ai=False
        )
        await suggester.suggest_mapping(
            headers=["C", "D"], doc_type="products", tenant_id="t2", use_ai=False
        )

        assert len(suggester._cache) >= 2

        suggester.clear_cache()
        assert len(suggester._cache) == 0


class TestMappingSuggestionDataclass:
    """Tests for MappingSuggestion dataclass."""

    def test_default_values(self):
        """Test default values in dataclass."""
        suggestion = MappingSuggestion(mappings={"a": "b"})

        assert suggestion.mappings == {"a": "b"}
        assert suggestion.transforms is None
        assert suggestion.defaults is None
        assert suggestion.confidence == 0.0
        assert suggestion.reasoning == ""
        assert suggestion.from_cache is False
        assert suggestion.provider == "heuristics"

    def test_all_values(self):
        """Test with all values provided."""
        suggestion = MappingSuggestion(
            mappings={"name": "name"},
            transforms={"date": "parse_date"},
            defaults={"category": "general"},
            confidence=0.95,
            reasoning="AI mapped columns",
            from_cache=True,
            provider="openai",
        )

        assert suggestion.confidence == 0.95
        assert suggestion.from_cache is True
        assert suggestion.provider == "openai"


class TestSingletonInstance:
    """Tests for the singleton instance."""

    def test_singleton_exists(self):
        """Test that singleton is properly initialized."""
        assert mapping_suggester is not None
        assert isinstance(mapping_suggester, MappingSuggester)

    def test_singleton_has_cache(self):
        """Test that singleton has cache dictionary."""
        assert hasattr(mapping_suggester, "_cache")
        assert isinstance(mapping_suggester._cache, dict)
