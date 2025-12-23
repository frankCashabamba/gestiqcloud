"""Tests for OCR service."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from app.modules.imports.services.ocr_service import (
    OCRService,
    OCRResult,
    DocumentLayout,
    ocr_service,
)


class TestOCRService:
    """Test OCRService functionality."""

    @pytest.fixture
    def service(self):
        """Create a fresh OCRService instance."""
        return OCRService()

    def test_supported_extensions(self, service):
        """Test that supported extensions are defined."""
        assert ".pdf" in service.SUPPORTED_EXTENSIONS
        assert ".png" in service.SUPPORTED_EXTENSIONS
        assert ".jpg" in service.SUPPORTED_EXTENSIONS
        assert ".jpeg" in service.SUPPORTED_EXTENSIONS
        assert ".tiff" in service.SUPPORTED_EXTENSIONS

    def test_supports_extension_pdf(self, service):
        """Test extension check for PDF."""
        assert service.supports_extension("/path/to/file.pdf") is True
        assert service.supports_extension("/path/to/file.PDF") is True

    def test_supports_extension_images(self, service):
        """Test extension check for images."""
        assert service.supports_extension("image.png") is True
        assert service.supports_extension("image.jpg") is True
        assert service.supports_extension("image.jpeg") is True

    def test_supports_extension_unsupported(self, service):
        """Test extension check for unsupported types."""
        assert service.supports_extension("file.xlsx") is False
        assert service.supports_extension("file.doc") is False
        assert service.supports_extension("file.txt") is False

    def test_is_available_no_dependencies(self):
        """Test availability check when dependencies are missing."""
        with patch.object(OCRService, "_check_dependencies"):
            service = OCRService()
            service._fitz_available = False
            service._tesseract_available = False
            assert service.is_available() is False

    def test_is_available_with_fitz(self):
        """Test availability when fitz is available."""
        with patch.object(OCRService, "_check_dependencies"):
            service = OCRService()
            service._fitz_available = True
            service._tesseract_available = False
            assert service.is_available() is True

    def test_is_available_with_tesseract(self):
        """Test availability when tesseract is available."""
        with patch.object(OCRService, "_check_dependencies"):
            service = OCRService()
            service._fitz_available = False
            service._tesseract_available = True
            assert service.is_available() is True

    @pytest.mark.asyncio
    async def test_extract_text_unsupported_extension(self, service):
        """Test that unsupported extensions raise error."""
        with pytest.raises(ValueError, match="Unsupported file type"):
            await service.extract_text("/path/to/file.xlsx")

    def test_detect_layout_invoice(self, service):
        """Test detection of invoice layout."""
        invoice_text = """
        FACTURA N° 001-0012345
        RUC: 12345678901
        Cliente: Empresa ABC
        Subtotal: $100.00
        IVA (18%): $18.00
        Total: $118.00
        """
        layout = service._detect_layout(invoice_text, [])
        assert layout == DocumentLayout.INVOICE

    def test_detect_layout_receipt(self, service):
        """Test detection of receipt layout."""
        receipt_text = """
        RECIBO DE PAGO
        Ticket #12345
        Total: $50.00
        Efectivo: $50.00
        Gracias por su compra
        """
        layout = service._detect_layout(receipt_text, [])
        assert layout == DocumentLayout.RECEIPT

    def test_detect_layout_bank_statement(self, service):
        """Test detection of bank statement layout."""
        bank_text = """
        EXTRACTO BANCARIO
        Cuenta: 1234567890
        IBAN: ES12 1234 5678 9012 3456
        Saldo anterior: $5,000.00
        Movimientos del mes
        Saldo actual: $4,500.00
        """
        layout = service._detect_layout(bank_text, [])
        assert layout == DocumentLayout.BANK_STATEMENT

    def test_detect_layout_with_tables(self, service):
        """Test that tables trigger TABLE layout."""
        generic_text = "Some random text without keywords"
        tables = [[["Header1", "Header2"], ["Value1", "Value2"]]]
        layout = service._detect_layout(generic_text, tables)
        assert layout == DocumentLayout.TABLE

    def test_detect_layout_unknown(self, service):
        """Test fallback to unknown layout."""
        generic_text = "Just some regular text with no special keywords"
        layout = service._detect_layout(generic_text, [])
        assert layout == DocumentLayout.UNKNOWN

    def test_extract_regions_from_data(self, service):
        """Test region extraction from OCR data."""
        ocr_data = {
            "text": ["Hello", "World", ""],
            "left": [10, 20, 30],
            "top": [100, 100, 100],
            "width": [50, 50, 50],
            "height": [20, 20, 20],
            "conf": [95, 80, 30],
        }

        regions = service._extract_regions_from_data(ocr_data)

        assert len(regions) == 2
        assert regions[0]["text"] == "Hello"
        assert regions[0]["confidence"] == 0.95
        assert regions[1]["text"] == "World"

    def test_extract_regions_filters_low_confidence(self, service):
        """Test that low confidence regions are filtered."""
        ocr_data = {
            "text": ["Good", "Bad"],
            "left": [10, 20],
            "top": [100, 100],
            "width": [50, 50],
            "height": [20, 20],
            "conf": [80, 40],
        }

        regions = service._extract_regions_from_data(ocr_data)

        assert len(regions) == 1
        assert regions[0]["text"] == "Good"


class TestOCRResult:
    """Test OCRResult dataclass."""

    def test_ocr_result_creation(self):
        """Test creating OCRResult with all fields."""
        result = OCRResult(
            text="Sample text",
            pages=1,
            layout=DocumentLayout.INVOICE,
            confidence=0.95,
            regions=[{"text": "Header", "bbox": [0, 0, 100, 20]}],
            tables=[[["A", "B"], ["1", "2"]]],
            metadata={"source": "embedded"},
            processing_time_ms=150.5,
        )

        assert result.text == "Sample text"
        assert result.pages == 1
        assert result.layout == DocumentLayout.INVOICE
        assert result.confidence == 0.95
        assert len(result.regions) == 1
        assert len(result.tables) == 1
        assert result.processing_time_ms == 150.5

    def test_ocr_result_defaults(self):
        """Test OCRResult with default values."""
        result = OCRResult(
            text="",
            pages=0,
            layout=DocumentLayout.UNKNOWN,
            confidence=0.0,
        )

        assert result.regions == []
        assert result.tables == []
        assert result.metadata == {}
        assert result.processing_time_ms == 0.0


class TestDocumentLayout:
    """Test DocumentLayout enum."""

    def test_layout_values(self):
        """Test all layout enum values."""
        assert DocumentLayout.INVOICE.value == "invoice"
        assert DocumentLayout.RECEIPT.value == "receipt"
        assert DocumentLayout.BANK_STATEMENT.value == "bank_statement"
        assert DocumentLayout.TABLE.value == "table"
        assert DocumentLayout.FORM.value == "form"
        assert DocumentLayout.UNKNOWN.value == "unknown"

    def test_layout_is_string_enum(self):
        """Test that layout values are strings."""
        assert isinstance(DocumentLayout.INVOICE, str)
        assert DocumentLayout.INVOICE == "invoice"


class TestOCRServiceWithMockedDependencies:
    """Tests with mocked PDF/OCR dependencies."""

    @pytest.fixture
    def mock_fitz_doc(self):
        """Create a mock fitz document."""
        mock_page = MagicMock()
        mock_page.get_text.return_value = "FACTURA\nRUC: 12345\nTotal: $100\nIVA: $18"
        mock_page.find_tables.return_value = []

        mock_doc = MagicMock()
        mock_doc.__iter__ = lambda self: iter([mock_page])
        mock_doc.__len__ = lambda self: 1
        mock_doc.close = MagicMock()

        return mock_doc

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires fitz module to be installed")
    async def test_process_pdf_with_embedded_text(self, mock_fitz_doc):
        """Test processing PDF with embedded text."""
        with patch.object(OCRService, "_check_dependencies"):
            service = OCRService()
            service._fitz_available = True
            service._tesseract_available = False

        with patch("app.modules.imports.services.ocr_service.fitz") as mock_fitz_module:
            mock_fitz_module.open.return_value = mock_fitz_doc
            result = await service._process_pdf("/fake/path.pdf")

        assert result.text is not None
        assert "FACTURA" in result.text
        assert result.pages == 1
        assert result.confidence > 0.9
        assert result.metadata.get("source") == "embedded"


class TestOCRServiceSingleton:
    """Test singleton instance."""

    def test_singleton_exists(self):
        """Test that singleton is initialized."""
        assert ocr_service is not None
        assert isinstance(ocr_service, OCRService)

    def test_singleton_has_logger(self):
        """Test that singleton has logger."""
        assert hasattr(ocr_service, "logger")
