"""Tests para LocalAIProvider (Fase D)."""

import pytest

from app.modules.imports.ai.cache import ClassificationCache
from app.modules.imports.ai.local_provider import LocalAIProvider


@pytest.fixture
def provider():
    """Crear instancia de LocalAIProvider."""
    return LocalAIProvider()


@pytest.fixture
def sample_invoice_text():
    """Texto de factura de ejemplo."""
    return """
    Invoice #INV-2025-001
    Date: 2025-01-15
    Vendor: Supplier ABC Inc.
    Customer: John Doe

    Total: $1,250.00
    Subtotal: $1,100.00
    Tax (12%): $150.00
    Amount Due: $1,250.00
    """


@pytest.fixture
def sample_bank_text():
    """Texto de transacción bancaria de ejemplo."""
    return """
    Bank Statement
    Account: 1234-5678-9012
    IBAN: ES9121000418450200051332
    Date: 2025-01-10

    Transaction Details:
    Date     | Description  | Debit  | Credit | Balance
    2025-01-10 | Opening Balance | - | 5000.00 | 5000.00
    2025-01-11 | Salary       | - | 3000.00 | 8000.00
    2025-01-12 | Rent Payment | 1500.00 | - | 6500.00
    """


@pytest.fixture
def sample_product_text():
    """Texto de productos de ejemplo."""
    return """
    Product Inventory
    SKU | Name | Category | Price | Quantity | Stock Status
    SKU-001 | Laptop Computer | Electronics | 899.99 | 50 | In Stock
    SKU-002 | Office Chair | Furniture | 249.50 | 120 | In Stock
    SKU-003 | Desk Lamp | Lighting | 45.00 | 200 | In Stock
    """


class TestLocalAIProviderClassification:
    """Tests de clasificación de documentos."""

    @pytest.mark.asyncio
    async def test_classify_invoice(self, provider, sample_invoice_text):
        """Clasificar documento como factura."""
        result = await provider.classify_document(
            text=sample_invoice_text,
            available_parsers=["csv_invoices", "products_excel", "csv_bank"],
        )

        assert result.suggested_parser == "csv_invoices"
        assert result.confidence >= 0.7
        assert result.provider == "local"
        assert "invoice" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_classify_bank_statement(self, provider, sample_bank_text):
        """Clasificar documento como extracto bancario."""
        result = await provider.classify_document(
            text=sample_bank_text, available_parsers=["csv_bank", "csv_invoices", "products_excel"]
        )

        assert result.suggested_parser == "csv_bank"
        assert result.confidence >= 0.7
        assert "bank" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_classify_products(self, provider, sample_product_text):
        """Clasificar documento como productos."""
        result = await provider.classify_document(
            text=sample_product_text, available_parsers=["products_excel", "csv_invoices"]
        )

        assert result.suggested_parser == "products_excel"
        assert result.confidence >= 0.6

    @pytest.mark.asyncio
    async def test_classify_with_metadata(self, provider, sample_invoice_text):
        """Clasificar con metadata adicional."""
        result = await provider.classify_document(
            text=sample_invoice_text,
            available_parsers=["csv_invoices"],
            doc_metadata={"filename": "invoice_2025_01.csv"},
        )

        assert result.suggested_parser == "csv_invoices"

    @pytest.mark.asyncio
    async def test_confidence_scores(self, provider, sample_invoice_text):
        """Verificar scores de confianza."""
        result = await provider.classify_document(
            text=sample_invoice_text,
            available_parsers=["csv_invoices", "csv_bank", "products_excel"],
        )

        # Verificar que tenemos probabilities
        assert "probabilities" in result.__dict__
        probabilities = result.probabilities

        # csv_invoices debe tener mayor probabilidad
        assert probabilities.get("csv_invoices", 0) >= probabilities.get("csv_bank", 0)


class TestLocalAIProviderFieldExtraction:
    """Tests de extracción de campos."""

    @pytest.mark.asyncio
    async def test_extract_invoice_fields(self, provider, sample_invoice_text):
        """Extraer campos de factura."""
        fields = await provider.extract_fields(
            text=sample_invoice_text,
            doc_type="invoice",
            expected_fields=["invoice_number", "total", "vendor", "date"],
        )

        assert fields.get("invoice_number") == "INV-2025-001"
        assert fields.get("total") == 1250.00
        assert "ABC" in fields.get("vendor", "")

    @pytest.mark.asyncio
    async def test_extract_missing_fields(self, provider, sample_invoice_text):
        """Manejar campos faltantes."""
        fields = await provider.extract_fields(
            text=sample_invoice_text,
            doc_type="invoice",
            expected_fields=["invoice_number", "total", "missing_field"],
        )

        # Debe incluir campos disponibles
        assert "invoice_number" in fields
        assert "total" in fields


class TestLocalAIProviderCache:
    """Tests de caché."""

    @pytest.mark.asyncio
    async def test_cache_enabled(self, sample_invoice_text):
        """Verificar que caché funciona."""
        provider = LocalAIProvider()
        available_parsers = ["csv_invoices", "csv_bank"]

        # Primera llamada
        result1 = await provider.classify_document(
            text=sample_invoice_text, available_parsers=available_parsers
        )

        # Segunda llamada (debe usar caché)
        result2 = await provider.classify_document(
            text=sample_invoice_text, available_parsers=available_parsers
        )

        # Resultados deben ser idénticos
        assert result1.suggested_parser == result2.suggested_parser
        assert result1.confidence == result2.confidence

    @pytest.mark.asyncio
    async def test_cache_miss_different_text(self, provider):
        """Caché miss con texto diferente."""
        text1 = "Invoice #001 Total: $100.00"
        text2 = "Bank Statement Account: 12345"
        available_parsers = ["csv_invoices", "csv_bank"]

        result1 = await provider.classify_document(text=text1, available_parsers=available_parsers)

        result2 = await provider.classify_document(text=text2, available_parsers=available_parsers)

        # Diferentes textos deben dar diferentes resultados
        assert result1.suggested_parser != result2.suggested_parser


class TestLocalAIProviderEdgeCases:
    """Tests de casos extremos."""

    @pytest.mark.asyncio
    async def test_empty_text(self, provider):
        """Manejar texto vacío."""
        result = await provider.classify_document(text="", available_parsers=["csv_invoices"])

        # Debe retornar resultado válido
        assert result.suggested_parser == "csv_invoices"
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_very_short_text(self, provider):
        """Manejar texto muy corto."""
        result = await provider.classify_document(text="A", available_parsers=["csv_invoices"])

        assert result.suggested_parser is not None

    @pytest.mark.asyncio
    async def test_single_parser(self, provider, sample_invoice_text):
        """Un único parser disponible."""
        result = await provider.classify_document(
            text=sample_invoice_text, available_parsers=["csv_invoices"]
        )

        assert result.suggested_parser == "csv_invoices"

    @pytest.mark.asyncio
    async def test_unicode_text(self, provider):
        """Manejar unicode."""
        text = "Factura #001 Total: €1.250,00 Proveedor: Empresa Española"
        result = await provider.classify_document(text=text, available_parsers=["csv_invoices"])

        assert result.suggested_parser == "csv_invoices"


class TestLocalAIProviderPerformance:
    """Tests de performance."""

    @pytest.mark.asyncio
    async def test_classification_latency(self, provider, sample_invoice_text):
        """Clasificación debe ser rápida (<100ms)."""
        import time

        start = time.time()
        result = await provider.classify_document(
            text=sample_invoice_text, available_parsers=["csv_invoices"]
        )
        elapsed = (time.time() - start) * 1000  # ms

        assert elapsed < 100
        assert result.suggested_parser is not None

    @pytest.mark.asyncio
    async def test_batch_classification(self, provider, sample_invoice_text):
        """Clasificar múltiples documentos."""
        texts = [sample_invoice_text] * 10
        available_parsers = ["csv_invoices", "csv_bank"]

        results = []
        for text in texts:
            result = await provider.classify_document(
                text=text, available_parsers=available_parsers
            )
            results.append(result)

        assert len(results) == 10
        assert all(r.suggested_parser == "csv_invoices" for r in results)


class TestClassificationCache:
    """Tests de ClassificationCache."""

    def test_cache_set_get(self):
        """Guardar y obtener del caché."""
        cache = ClassificationCache(ttl_seconds=3600)

        result = {"suggested_parser": "csv_invoices", "confidence": 0.85}
        text = "Invoice text"
        available_parsers = ["csv_invoices"]

        cache.set(text, available_parsers, result)
        cached = cache.get(text, available_parsers)

        assert cached == result

    def test_cache_miss(self):
        """Caché miss retorna None."""
        cache = ClassificationCache()

        cached = cache.get("unknown text", ["csv_invoices"])
        assert cached is None

    def test_cache_clear(self):
        """Limpiar caché."""
        cache = ClassificationCache()

        result = {"suggested_parser": "csv_invoices"}
        cache.set("text", ["csv_invoices"], result)

        cache.clear()
        cached = cache.get("text", ["csv_invoices"])

        assert cached is None

    def test_cache_size(self):
        """Obtener tamaño del caché."""
        cache = ClassificationCache()

        for i in range(5):
            cache.set(f"text_{i}", ["parser"], {"result": i})

        size = cache.size()
        assert size == 5
