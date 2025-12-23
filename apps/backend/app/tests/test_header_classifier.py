"""Tests for header classifier ML module."""

import pytest


class TestHeaderClassifier:
    """Test cases for HeaderClassifier."""

    def test_classify_products_headers(self):
        """Should classify product headers correctly."""
        from app.modules.imports.services.header_classifier import header_classifier

        result = header_classifier.classify(
            headers=["nombre", "precio", "stock", "categoria"],
            file_extension="xlsx",
        )
        assert result.doc_type == "products"
        assert result.suggested_parser == "products_excel"
        assert result.confidence >= 0.5

    def test_classify_bank_headers(self):
        """Should classify bank transaction headers correctly."""
        from app.modules.imports.services.header_classifier import header_classifier

        result = header_classifier.classify(
            headers=["fecha", "concepto", "importe", "saldo"],
            file_extension="csv",
        )
        assert result.doc_type == "bank_transactions"
        assert result.suggested_parser == "csv_bank"
        assert result.confidence >= 0.5

    def test_classify_invoice_headers(self):
        """Should classify invoice headers correctly."""
        from app.modules.imports.services.header_classifier import header_classifier

        result = header_classifier.classify(
            headers=["factura", "cliente", "total", "iva"],
            file_extension="xlsx",
        )
        assert result.doc_type == "invoices"
        assert result.suggested_parser == "xlsx_invoices"
        assert result.confidence >= 0.5

    def test_classify_expenses_headers(self):
        """Should classify expense headers correctly."""
        from app.modules.imports.services.header_classifier import header_classifier

        result = header_classifier.classify(
            headers=["gasto", "categoria", "monto", "fecha", "comprobante"],
            file_extension="xlsx",
        )
        assert result.doc_type == "expenses"
        assert result.suggested_parser == "xlsx_expenses"
        assert result.confidence >= 0.5

    def test_classify_english_headers(self):
        """Should classify English headers correctly."""
        from app.modules.imports.services.header_classifier import header_classifier

        result = header_classifier.classify(
            headers=["product", "price", "quantity", "sku"],
            file_extension="csv",
        )
        assert result.doc_type == "products"
        assert result.suggested_parser == "csv_products"

    def test_get_features(self):
        """Should extract features from headers."""
        from app.modules.imports.services.header_classifier import header_classifier

        features = header_classifier.get_features(
            headers=["nombre", "precio", "stock"],
        )
        assert "keyword_scores" in features
        assert "products" in features["keyword_scores"]
        assert features["keyword_scores"]["products"] > 0

    def test_classification_result_has_probabilities(self):
        """Should return probabilities for all doc types."""
        from app.modules.imports.services.header_classifier import header_classifier

        result = header_classifier.classify(
            headers=["nombre", "precio"],
            file_extension="xlsx",
        )
        assert "products" in result.probabilities
        assert "bank_transactions" in result.probabilities
        assert "invoices" in result.probabilities
        assert "expenses" in result.probabilities

    def test_fallback_for_unknown_headers(self):
        """Should fallback gracefully for unknown headers."""
        from app.modules.imports.services.header_classifier import header_classifier

        result = header_classifier.classify(
            headers=["col1", "col2", "xyz123"],
            file_extension="xlsx",
        )
        assert result.suggested_parser is not None
        assert result.confidence <= 0.5

    def test_extension_affects_parser_selection(self):
        """Parser should match file extension."""
        from app.modules.imports.services.header_classifier import header_classifier

        result_xlsx = header_classifier.classify(
            headers=["nombre", "precio", "stock"],
            file_extension="xlsx",
        )
        result_csv = header_classifier.classify(
            headers=["nombre", "precio", "stock"],
            file_extension="csv",
        )

        assert result_xlsx.suggested_parser == "products_excel"
        assert result_csv.suggested_parser == "csv_products"
