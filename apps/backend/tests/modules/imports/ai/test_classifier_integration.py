"""Tests de integración de FileClassifier con IA (Fase D)."""

import pytest

from app.modules.imports.services.classifier import FileClassifier


@pytest.fixture
def classifier():
    """Crear instancia de FileClassifier."""
    return FileClassifier()


@pytest.fixture
def sample_csv_invoice(tmp_path):
    """Crear CSV de factura de prueba."""
    csv_file = tmp_path / "invoices.csv"
    csv_content = """invoice_number,date,vendor,total,tax
INV-001,2025-01-15,Supplier A,1250.00,150.00
INV-002,2025-01-16,Supplier B,2500.00,300.00
INV-003,2025-01-17,Supplier C,500.00,60.00
"""
    csv_file.write_text(csv_content)
    return str(csv_file)


@pytest.fixture
def sample_csv_bank(tmp_path):
    """Crear CSV de banco de prueba."""
    csv_file = tmp_path / "transactions.csv"
    csv_content = """date,amount,direction,account,iban
2025-01-15,1000.00,credit,checking,ES9121000418450200051332
2025-01-16,500.00,debit,checking,ES9121000418450200051332
2025-01-17,2000.00,credit,savings,ES9121000418450200051333
"""
    csv_file.write_text(csv_content)
    return str(csv_file)


@pytest.fixture
def sample_excel(tmp_path):
    """Crear archivo Excel de prueba."""
    import openpyxl

    excel_file = tmp_path / "products.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active

    # Headers
    ws.append(["SKU", "Name", "Price", "Quantity", "Category"])
    # Data rows
    ws.append(["SKU-001", "Laptop", 899.99, 50, "Electronics"])
    ws.append(["SKU-002", "Mouse", 29.99, 200, "Electronics"])

    wb.save(excel_file)
    return str(excel_file)


@pytest.fixture
def sample_xml_invoice(tmp_path):
    """Crear archivo XML de factura."""
    xml_file = tmp_path / "invoice.xml"
    xml_content = """<?xml version="1.0"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">
    <cbc:ID>INV-001</cbc:ID>
    <cbc:IssueDate>2025-01-15</cbc:IssueDate>
    <cac:AccountingSupplierParty>
        <cac:Party>
            <cbc:Name>Supplier ABC</cbc:Name>
        </cac:Party>
    </cac:AccountingSupplierParty>
    <cac:LegalMonetaryTotal>
        <cbc:LineExtensionAmount>1100.00</cbc:LineExtensionAmount>
        <cbc:TaxTotal>150.00</cbc:TaxTotal>
        <cbc:PayableAmount>1250.00</cbc:PayableAmount>
    </cac:LegalMonetaryTotal>
</Invoice>
"""
    xml_file.write_text(xml_content)
    return str(xml_file)


class TestFileClassifierBasic:
    """Tests básicos de FileClassifier."""

    def test_classify_csv_invoice(self, classifier, sample_csv_invoice):
        """Clasificar CSV de factura."""
        result = classifier.classify_file(sample_csv_invoice, "invoices.csv")

        assert result["suggested_parser"] in ["csv_invoices", "csv_bank"]
        assert result["confidence"] > 0
        assert "available_parsers" in result

    def test_classify_csv_bank(self, classifier, sample_csv_bank):
        """Clasificar CSV de banco."""
        result = classifier.classify_file(sample_csv_bank, "transactions.csv")

        assert result["suggested_parser"] in ["csv_bank", "csv_invoices"]
        assert result["confidence"] > 0

    def test_classify_excel(self, classifier, sample_excel):
        """Clasificar archivo Excel."""
        result = classifier.classify_file(sample_excel, "products.xlsx")

        assert result["suggested_parser"] in ["products_excel", "generic_excel"]
        assert result["confidence"] > 0.5

    def test_classify_xml_invoice(self, classifier, sample_xml_invoice):
        """Clasificar XML de factura."""
        result = classifier.classify_file(sample_xml_invoice, "invoice.xml")

        assert result["suggested_parser"] in ["xml_invoice", "xml_camt053_bank"]
        assert result["confidence"] > 0.5


class TestFileClassifierWithAI:
    """Tests de FileClassifier con IA."""

    @pytest.mark.asyncio
    async def test_classify_with_ai_invoice(self, classifier, sample_csv_invoice):
        """Clasificar CSV con IA."""
        result = await classifier.classify_file_with_ai(sample_csv_invoice, "invoices.csv")

        assert "suggested_parser" in result
        assert "confidence" in result
        assert result["confidence"] >= 0

    @pytest.mark.asyncio
    async def test_classify_with_ai_bank(self, classifier, sample_csv_bank):
        """Clasificar banco con IA."""
        result = await classifier.classify_file_with_ai(sample_csv_bank, "transactions.csv")

        assert result["suggested_parser"] is not None
        assert result["confidence"] >= 0

    @pytest.mark.asyncio
    async def test_ai_enhancement_flag(self, classifier, sample_csv_invoice):
        """Verificar flag de mejora por IA."""
        result = await classifier.classify_file_with_ai(sample_csv_invoice, "invoices.csv")

        # Si confidence base era baja, AI puede haber mejorado
        if result.get("enhanced_by_ai"):
            assert "ai_provider" in result

    @pytest.mark.asyncio
    async def test_fallback_if_ai_fails(self, classifier, sample_csv_invoice):
        """Fallback a clasificación base si IA falla."""
        # Debe retornar resultado válido incluso si IA falla
        result = await classifier.classify_file_with_ai(sample_csv_invoice, "invoices.csv")

        assert result is not None
        assert "suggested_parser" in result


class TestFileClassifierTextExtraction:
    """Tests de extracción de texto."""

    def test_extract_text_csv(self, classifier, sample_csv_invoice):
        """Extraer texto de CSV."""
        text = classifier._extract_text(sample_csv_invoice, "invoices.csv")

        assert len(text) > 0
        assert "invoice_number" in text.lower() or "vendor" in text.lower()

    def test_extract_text_excel(self, classifier, sample_excel):
        """Extraer texto de Excel."""
        text = classifier._extract_text(sample_excel, "products.xlsx")

        assert len(text) > 0
        assert "SKU" in text or "Name" in text or "Price" in text

    def test_extract_text_xml(self, classifier, sample_xml_invoice):
        """Extraer texto de XML."""
        text = classifier._extract_text(sample_xml_invoice, "invoice.xml")

        assert len(text) > 0
        assert "Invoice" in text or "Supplier" in text

    def test_extract_text_nonexistent(self, classifier):
        """Manejar archivo que no existe."""
        text = classifier._extract_text("/nonexistent/file.csv", "file.csv")

        # Debe retornar string vacío
        assert text == ""


class TestFileClassifierEdgeCases:
    """Tests de casos extremos."""

    def test_unsupported_extension(self, classifier):
        """Extensión no soportada."""
        result = classifier.classify_file("/path/to/file.pdf", "file.pdf")

        assert result["suggested_parser"] is None
        assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_empty_file(self, classifier, tmp_path):
        """Archivo vacío."""
        empty_file = tmp_path / "empty.csv"
        empty_file.write_text("")

        result = await classifier.classify_file_with_ai(str(empty_file), "empty.csv")

        # Debe manejar gracefully
        assert result is not None

    @pytest.mark.asyncio
    async def test_corrupted_excel(self, classifier, tmp_path):
        """Archivo Excel corrupto."""
        corrupted_file = tmp_path / "corrupted.xlsx"
        corrupted_file.write_text("not a valid excel file")

        result = await classifier.classify_file_with_ai(str(corrupted_file), "corrupted.xlsx")

        # Debe retornar clasificación base
        assert result is not None
        assert "suggested_parser" in result


class TestFileClassifierPerformance:
    """Tests de performance."""

    def test_classification_fast(self, classifier, sample_csv_invoice):
        """Clasificación base debe ser rápida."""
        import time

        start = time.time()
        result = classifier.classify_file(sample_csv_invoice, "invoices.csv")
        elapsed = (time.time() - start) * 1000  # ms

        # Debe ser muy rápido (<50ms para heurísticas)
        assert elapsed < 50
        assert result["suggested_parser"] is not None

    @pytest.mark.asyncio
    async def test_classification_with_ai_reasonable(self, classifier, sample_csv_invoice):
        """Clasificación con IA debe ser razonable (<200ms para local)."""
        import time

        start = time.time()
        result = await classifier.classify_file_with_ai(sample_csv_invoice, "invoices.csv")
        elapsed = (time.time() - start) * 1000  # ms

        # Con IA local debe ser < 200ms
        assert elapsed < 200
        assert result["suggested_parser"] is not None


class TestClassifierMultipleFiles:
    """Tests con múltiples archivos."""

    @pytest.mark.asyncio
    async def test_classify_multiple(
        self, classifier, sample_csv_invoice, sample_csv_bank, sample_excel
    ):
        """Clasificar múltiples archivos."""
        files = [
            (sample_csv_invoice, "invoices.csv"),
            (sample_csv_bank, "transactions.csv"),
            (sample_excel, "products.xlsx"),
        ]

        results = []
        for file_path, filename in files:
            result = await classifier.classify_file_with_ai(file_path, filename)
            results.append(result)

        assert len(results) == 3

        # Cada uno debe tener clasificación válida
        for result in results:
            assert result["suggested_parser"] is not None
            assert result["confidence"] >= 0


class TestClassifierIntegrationWithParsers:
    """Tests de integración con parsers."""

    def test_classifier_suggests_valid_parser(self, classifier, sample_csv_invoice):
        """El parser sugerido debe estar registrado."""
        from app.modules.imports.parsers import registry

        result = classifier.classify_file(sample_csv_invoice, "invoices.csv")
        suggested = result["suggested_parser"]

        if suggested:
            parser = registry.get(suggested)
            assert parser is not None

    @pytest.mark.asyncio
    async def test_classifier_with_ai_suggests_valid_parser(self, classifier, sample_csv_invoice):
        """Parser sugerido por IA debe estar registrado."""
        from app.modules.imports.parsers import registry

        result = await classifier.classify_file_with_ai(sample_csv_invoice, "invoices.csv")
        suggested = result["suggested_parser"]

        if suggested:
            parser = registry.get(suggested)
            assert parser is not None
