"""Extended tests for MappingSuggester - Sprint-specific tests."""

import pytest

from app.modules.imports.ai.mapping_suggester import MappingSuggester


class TestMappingSuggesterProducts:
    """Test mapping suggestions for products."""

    @pytest.mark.asyncio
    async def test_suggest_products_mapping(self):
        """Test sugerencia de mapping para productos."""
        suggester = MappingSuggester()
        suggester.clear_cache()

        result = await suggester.suggest_mapping(
            headers=["nombre", "precio", "cantidad"],
            sample_rows=[["Laptop", "999.99", "10"]],
            doc_type="products",
            use_ai=False,
        )

        assert result.mappings.get("nombre") == "name"
        assert result.mappings.get("precio") == "price"
        assert result.mappings.get("cantidad") == "stock"
        assert result.provider == "heuristics"

    @pytest.mark.asyncio
    async def test_suggest_products_english_headers(self):
        """Test mapping with English headers."""
        suggester = MappingSuggester()

        result = await suggester.suggest_mapping(
            headers=["product_name", "unit_price", "quantity", "sku"],
            sample_rows=[["Widget", "50.00", "100", "WDG-001"]],
            doc_type="products",
            use_ai=False,
        )

        assert "unit_price" in result.mappings
        assert result.mappings.get("sku") == "sku"

    @pytest.mark.asyncio
    async def test_suggest_products_with_category(self):
        """Test mapping with category field."""
        suggester = MappingSuggester()

        result = await suggester.suggest_mapping(
            headers=["producto", "categoria", "costo", "stock"],
            sample_rows=[["Item A", "Electronics", "25.00", "50"]],
            doc_type="products",
            use_ai=False,
        )

        assert result.mappings.get("producto") == "name"
        assert result.mappings.get("categoria") == "category"
        assert result.mappings.get("costo") == "cost"


class TestMappingSuggesterBankTransactions:
    """Test mapping suggestions for bank transactions."""

    @pytest.mark.asyncio
    async def test_suggest_bank_mapping(self):
        """Test mapping for bank transaction headers."""
        suggester = MappingSuggester()

        result = await suggester.suggest_mapping(
            headers=["fecha", "importe", "concepto", "saldo"],
            sample_rows=[["2024-01-15", "1500.00", "Transferencia", "5000.00"]],
            doc_type="bank_transactions",
            use_ai=False,
        )

        assert result.mappings.get("fecha") == "value_date"
        assert result.mappings.get("importe") == "amount"
        assert result.mappings.get("concepto") == "narrative"
        assert result.mappings.get("saldo") == "balance"

    @pytest.mark.asyncio
    async def test_suggest_bank_with_iban(self):
        """Test mapping with IBAN field."""
        suggester = MappingSuggester()

        result = await suggester.suggest_mapping(
            headers=["fecha_valor", "iban", "beneficiario", "monto"],
            sample_rows=[["2024-01-15", "ES12345678", "Cliente A", "500.00"]],
            doc_type="bank_transactions",
            use_ai=False,
        )

        assert result.mappings.get("iban") == "iban"
        assert result.mappings.get("beneficiario") == "counterparty"


class TestMappingSuggesterInvoices:
    """Test mapping suggestions for invoices."""

    @pytest.mark.asyncio
    async def test_suggest_invoice_mapping(self):
        """Test mapping for invoice headers."""
        suggester = MappingSuggester()

        result = await suggester.suggest_mapping(
            headers=["numero_factura", "proveedor", "ruc", "total", "iva"],
            sample_rows=[["F-001", "Proveedor A", "12345678", "1180.00", "180.00"]],
            doc_type="invoices",
            use_ai=False,
        )

        assert result.mappings.get("proveedor") == "vendor_name"
        assert result.mappings.get("ruc") == "vendor_tax_id"
        assert result.mappings.get("total") == "total"
        assert result.mappings.get("iva") == "tax"

    @pytest.mark.asyncio
    async def test_suggest_invoice_with_dates(self):
        """Test mapping with date fields."""
        suggester = MappingSuggester()

        result = await suggester.suggest_mapping(
            headers=["factura", "fecha_emision", "vencimiento", "subtotal"],
            sample_rows=[["F-001", "2024-01-15", "2024-02-15", "1000.00"]],
            doc_type="invoices",
            use_ai=False,
        )

        assert result.mappings.get("fecha_emision") == "issue_date"
        assert result.mappings.get("vencimiento") == "due_date"

        assert result.transforms is not None
        if "fecha_emision" in result.transforms:
            assert result.transforms["fecha_emision"] == "parse_date"


class TestMappingSuggesterExpenses:
    """Test mapping suggestions for expenses."""

    @pytest.mark.asyncio
    async def test_suggest_expenses_mapping(self):
        """Test mapping for expense headers."""
        suggester = MappingSuggester()

        result = await suggester.suggest_mapping(
            headers=["gasto", "categoria", "monto", "fecha_gasto"],
            sample_rows=[["Suministros", "Oficina", "150.00", "2024-01-15"]],
            doc_type="expenses",
            use_ai=False,
        )

        assert result.mappings.get("gasto") == "description"
        assert result.mappings.get("categoria") == "category"
        assert result.mappings.get("monto") == "amount"


class TestMappingSuggesterCache:
    """Test caching functionality."""

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        """Test que el cache funciona."""
        import uuid

        suggester = MappingSuggester()
        suggester.clear_cache()

        unique_id = str(uuid.uuid4())[:8]
        headers = [f"UniqueCacheTestHeader1_{unique_id}", f"UniqueCacheTestHeader2_{unique_id}"]
        unique_tenant = f"cache-test-tenant-{unique_id}"

        result1 = await suggester.suggest_mapping(
            headers=headers,
            doc_type="products",
            tenant_id=unique_tenant,
            use_ai=False,
        )

        assert result1.from_cache is False

        result2 = await suggester.suggest_mapping(
            headers=headers,
            doc_type="products",
            tenant_id=unique_tenant,
            use_ai=False,
        )

        assert result2.from_cache is True
        suggester.clear_cache(unique_tenant)

    @pytest.mark.asyncio
    async def test_cache_miss_different_headers(self):
        """Test cache miss with different headers."""
        suggester = MappingSuggester()
        suggester.clear_cache()

        result1 = await suggester.suggest_mapping(
            headers=["header1", "header2"],
            doc_type="products",
            use_ai=False,
        )

        result2 = await suggester.suggest_mapping(
            headers=["header3", "header4"],
            doc_type="products",
            use_ai=False,
        )

        assert result1.from_cache is False
        assert result2.from_cache is False

    @pytest.mark.asyncio
    async def test_cache_miss_different_doc_type(self):
        """Test cache miss with different doc type."""
        suggester = MappingSuggester()
        suggester.clear_cache()

        headers = ["nombre", "precio"]

        result1 = await suggester.suggest_mapping(
            headers=headers,
            doc_type="products",
            use_ai=False,
        )

        result2 = await suggester.suggest_mapping(
            headers=headers,
            doc_type="expenses",
            use_ai=False,
        )

        assert result1.from_cache is False
        assert result2.from_cache is False

    def test_get_stats(self):
        """Test getting cache stats."""
        suggester = MappingSuggester()

        stats = suggester.get_stats()

        assert "in_memory_entries" in stats
        assert "redis_available" in stats


class TestMappingSuggesterTransforms:
    """Test transform suggestions."""

    @pytest.mark.asyncio
    async def test_date_transforms(self):
        """Test that date fields get parse_date transform."""
        suggester = MappingSuggester()

        result = await suggester.suggest_mapping(
            headers=["fecha", "fecha_valor", "vencimiento"],
            doc_type="bank_transactions",
            use_ai=False,
        )

        assert result.transforms is not None
        date_transforms = [k for k, v in result.transforms.items() if v == "parse_date"]
        assert len(date_transforms) > 0

    @pytest.mark.asyncio
    async def test_number_transforms(self):
        """Test that numeric fields get parse_number transform."""
        suggester = MappingSuggester()

        result = await suggester.suggest_mapping(
            headers=["precio", "subtotal", "total", "iva"],
            doc_type="invoices",
            use_ai=False,
        )

        assert result.transforms is not None
        number_transforms = [k for k, v in result.transforms.items() if v == "parse_number"]
        assert len(number_transforms) > 0


class TestMappingSuggesterConfidence:
    """Test confidence calculations."""

    @pytest.mark.asyncio
    async def test_high_confidence_all_matched(self):
        """Test high confidence when all headers match."""
        suggester = MappingSuggester()

        result = await suggester.suggest_mapping(
            headers=["nombre", "precio", "stock", "sku"],
            doc_type="products",
            use_ai=False,
        )

        assert result.confidence >= 0.8

    @pytest.mark.asyncio
    async def test_low_confidence_few_matches(self):
        """Test low confidence when few headers match."""
        suggester = MappingSuggester()

        result = await suggester.suggest_mapping(
            headers=["xyz123", "abc456", "unknown1", "unknown2"],
            doc_type="products",
            use_ai=False,
        )

        assert result.confidence < 0.5

    @pytest.mark.asyncio
    async def test_zero_confidence_no_matches(self):
        """Test zero confidence when no headers match."""
        suggester = MappingSuggester()

        result = await suggester.suggest_mapping(
            headers=["completely_random_1", "completely_random_2"],
            doc_type="products",
            use_ai=False,
        )

        assert result.confidence == 0.0
        assert len(result.mappings) == 0


class TestMappingSuggesterReasoning:
    """Test reasoning/explanation generation."""

    @pytest.mark.asyncio
    async def test_reasoning_includes_counts(self):
        """Test that reasoning includes match counts."""
        suggester = MappingSuggester()

        result = await suggester.suggest_mapping(
            headers=["nombre", "precio", "unknown"],
            doc_type="products",
            use_ai=False,
        )

        assert "2/3" in result.reasoning or "2" in result.reasoning

    @pytest.mark.asyncio
    async def test_reasoning_mentions_unmapped(self):
        """Test that reasoning mentions unmapped columns."""
        suggester = MappingSuggester()

        result = await suggester.suggest_mapping(
            headers=["nombre", "xyz123"],
            doc_type="products",
            use_ai=False,
        )

        if len(result.mappings) < 2:
            assert "unmapped" in result.reasoning.lower()
