"""Tests for SmartRouter."""

import csv
from pathlib import Path
from unittest.mock import AsyncMock, patch

import openpyxl
import pytest


class TestSmartRouter:
    """Test SmartRouter analysis functionality."""

    @pytest.fixture
    def router(self):
        from app.modules.imports.services.smart_router import SmartRouter

        return SmartRouter()

    @pytest.fixture
    def sample_products_excel(self, tmp_path) -> Path:
        """Create a sample products Excel file."""
        file_path = tmp_path / "products.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["nombre", "precio", "stock", "categoria", "sku"])
        ws.append(["Laptop", 999.99, 10, "Electrónica", "LAP-001"])
        ws.append(["Mouse", 29.99, 50, "Accesorios", "MOU-001"])
        ws.append(["Teclado", 49.99, 30, "Accesorios", "TEC-001"])
        wb.save(file_path)
        return file_path

    @pytest.fixture
    def sample_bank_csv(self, tmp_path) -> Path:
        """Create a sample bank CSV file."""
        file_path = tmp_path / "bank.csv"
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["fecha", "concepto", "importe", "saldo"])
            writer.writerow(["2024-01-15", "Transferencia recibida", 1500.00, 5000.00])
            writer.writerow(["2024-01-16", "Pago servicios", -200.00, 4800.00])
        return file_path

    @pytest.fixture
    def sample_ambiguous_csv(self, tmp_path) -> Path:
        """Create an ambiguous CSV file with unknown headers."""
        file_path = tmp_path / "ambiguous.csv"
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["col1", "col2", "col3"])
            writer.writerow(["value1", "value2", "value3"])
        return file_path

    @pytest.fixture
    def sample_invoice_excel(self, tmp_path) -> Path:
        """Create a sample invoice Excel file."""
        file_path = tmp_path / "invoices.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["factura", "cliente", "total", "iva", "fecha"])
        ws.append(["F-001", "Cliente A", 1180.00, 180.00, "2024-01-20"])
        ws.append(["F-002", "Cliente B", 590.00, 90.00, "2024-01-21"])
        wb.save(file_path)
        return file_path

    @pytest.mark.asyncio
    async def test_analyze_excel_products(self, router, sample_products_excel):
        """Test análisis de Excel de productos."""
        with patch.object(router, "classifier") as mock_classifier:
            mock_classifier.classify_file.return_value = {
                "suggested_parser": "products_excel",
                "confidence": 0.85,
                "reason": "Detected product headers",
            }

            result = await router.analyze_file(
                file_path=str(sample_products_excel),
                filename="products.xlsx",
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                tenant_id="test-tenant",
            )

        assert result.suggested_parser is not None
        assert result.confidence > 0
        assert len(result.headers_sample) > 0
        assert "nombre" in result.headers_sample
        assert result.decision_log is not None
        assert len(result.decision_log) > 0

    @pytest.mark.asyncio
    async def test_analyze_csv_bank(self, router, sample_bank_csv):
        """Test análisis de CSV bancario."""
        with patch.object(router, "classifier") as mock_classifier:
            mock_classifier.classify_file.return_value = {
                "suggested_parser": "csv_bank",
                "confidence": 0.8,
                "reason": "Detected bank transaction headers",
            }

            result = await router.analyze_file(
                file_path=str(sample_bank_csv),
                filename="bank.csv",
                content_type="text/csv",
            )

        assert result.suggested_parser is not None
        assert len(result.headers_sample) >= 4
        assert "fecha" in result.headers_sample
        assert "importe" in result.headers_sample

    @pytest.mark.asyncio
    async def test_analyze_requires_confirmation(self, router, sample_ambiguous_csv):
        """Test que archivos ambiguos requieren confirmación."""
        with patch.object(router, "classifier") as mock_classifier:
            mock_classifier.classify_file.return_value = {
                "suggested_parser": "generic_csv",
                "confidence": 0.3,
                "reason": "Low confidence classification",
            }
            mock_classifier.classify_file_with_ai = AsyncMock(
                return_value={
                    "enhanced_by_ai": False,
                    "confidence": 0.4,
                }
            )

            result = await router.analyze_file(
                file_path=str(sample_ambiguous_csv),
                filename="ambiguous.csv",
            )

        assert result.requires_confirmation is True
        assert result.confidence < 0.7

    @pytest.mark.asyncio
    async def test_decision_log_populated(self, router, sample_products_excel):
        """Verificar que decision_log tiene todos los pasos."""
        with patch.object(router, "classifier") as mock_classifier:
            mock_classifier.classify_file.return_value = {
                "suggested_parser": "products_excel",
                "confidence": 0.9,
                "reason": "Product headers detected",
            }

            result = await router.analyze_file(
                file_path=str(sample_products_excel),
                filename="products.xlsx",
            )

        steps = [entry.get("step") for entry in result.decision_log]
        assert "file_detection" in steps
        assert "headers_extraction" in steps
        assert "dispatcher_heuristics" in steps
        assert "classifier_analysis" in steps
        assert "final_decision" in steps

    @pytest.mark.asyncio
    async def test_headers_extraction_excel(self, router, sample_products_excel):
        """Test extracción correcta de headers de Excel."""
        headers = router._extract_headers(
            str(sample_products_excel),
            ".xlsx",
        )

        assert len(headers) == 5
        assert "nombre" in headers
        assert "precio" in headers
        assert "stock" in headers

    @pytest.mark.asyncio
    async def test_headers_extraction_csv(self, router, sample_bank_csv):
        """Test extracción correcta de headers de CSV."""
        headers = router._extract_headers(
            str(sample_bank_csv),
            ".csv",
        )

        assert len(headers) == 4
        assert "fecha" in headers
        assert "concepto" in headers

    def test_extract_sample_rows_excel(self, router, sample_products_excel):
        """Test extracción de filas de muestra de Excel."""
        headers = router._extract_headers(str(sample_products_excel), ".xlsx")
        rows = router._extract_sample_rows(str(sample_products_excel), ".xlsx", headers)

        assert len(rows) >= 1
        assert len(rows) <= 3
        assert "Laptop" in str(rows[0])

    def test_extract_sample_rows_csv(self, router, sample_bank_csv):
        """Test extracción de filas de muestra de CSV."""
        headers = router._extract_headers(str(sample_bank_csv), ".csv")
        rows = router._extract_sample_rows(str(sample_bank_csv), ".csv", headers)

        assert len(rows) >= 1
        assert any("Transferencia" in str(row) for row in rows)

    @pytest.mark.asyncio
    async def test_mapping_suggestion_generated(self, router, sample_products_excel):
        """Test que se genera sugerencia de mapping."""
        with patch.object(router, "classifier") as mock_classifier:
            mock_classifier.classify_file.return_value = {
                "suggested_parser": "products_excel",
                "confidence": 0.9,
                "reason": "Product file",
            }

            result = await router.analyze_file(
                file_path=str(sample_products_excel),
                filename="products.xlsx",
            )

        assert result.mapping_suggestion is not None or result.mapping_confidence is not None

    @pytest.mark.asyncio
    async def test_available_parsers_list(self, router, sample_products_excel):
        """Test que se retorna lista de parsers disponibles."""
        with patch.object(router, "classifier") as mock_classifier:
            mock_classifier.classify_file.return_value = {
                "suggested_parser": "products_excel",
                "confidence": 0.9,
            }

            result = await router.analyze_file(
                file_path=str(sample_products_excel),
                filename="products.xlsx",
            )

        assert len(result.available_parsers) > 0

    @pytest.mark.asyncio
    async def test_ai_enhancement_triggered_on_low_confidence(self, router, sample_ambiguous_csv):
        """Test que AI enhancement se intenta cuando confidence es baja."""
        with patch.object(router, "classifier") as mock_classifier:
            mock_classifier.classify_file.return_value = {
                "suggested_parser": "generic_csv",
                "confidence": 0.4,
                "reason": "Low confidence",
            }
            mock_classifier.classify_file_with_ai = AsyncMock(
                return_value={
                    "enhanced_by_ai": True,
                    "ai_provider": "openai",
                    "confidence": 0.85,
                    "suggested_parser": "csv_products",
                    "reasoning": "AI detected product data",
                }
            )

            result = await router.analyze_file(
                file_path=str(sample_ambiguous_csv),
                filename="ambiguous.csv",
            )

            mock_classifier.classify_file_with_ai.assert_called_once()
            ai_steps = [e for e in result.decision_log if "ai_enhancement" in e.get("step", "")]
            assert len(ai_steps) > 0


class TestSmartRouterSuggestMapping:
    """Test _suggest_mapping method."""

    @pytest.fixture
    def router(self):
        from app.modules.imports.services.smart_router import SmartRouter

        return SmartRouter()

    def test_suggest_mapping_products(self, router):
        """Test mapping suggestion for products."""
        headers = ["nombre", "precio", "cantidad", "codigo"]
        mapping = router._suggest_mapping(headers, "products")

        assert mapping is not None
        assert mapping.get("nombre") == "name"
        assert mapping.get("precio") == "price"

    def test_suggest_mapping_bank(self, router):
        """Test mapping suggestion for bank transactions."""
        headers = ["fecha", "importe", "concepto", "saldo"]
        mapping = router._suggest_mapping(headers, "bank_transactions")

        assert mapping is not None
        assert mapping.get("fecha") == "date"
        assert mapping.get("importe") == "amount"

    def test_suggest_mapping_empty_headers(self, router):
        """Test mapping with empty headers."""
        mapping = router._suggest_mapping([], "products")
        assert mapping is None

    def test_suggest_mapping_unknown_doc_type(self, router):
        """Test mapping with unknown doc type."""
        headers = ["nombre", "precio"]
        mapping = router._suggest_mapping(headers, "unknown_type")
        assert mapping is None


class TestSmartRouterSingleton:
    """Test singleton instance."""

    def test_singleton_exists(self):
        """Test that singleton is properly initialized."""
        from app.modules.imports.services.smart_router import smart_router

        assert smart_router is not None

    def test_singleton_has_classifier(self):
        """Test that singleton has classifier."""
        from app.modules.imports.services.smart_router import smart_router

        assert hasattr(smart_router, "classifier")
