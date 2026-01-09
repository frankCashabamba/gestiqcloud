"""OCR service using PyMuPDF + Tesseract for PDF/image text extraction."""

from __future__ import annotations

import io
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger("imports.ocr")


class DocumentLayout(str, Enum):
    """Tipo de layout detectado."""

    INVOICE = "invoice"
    RECEIPT = "receipt"
    BANK_STATEMENT = "bank_statement"
    TICKET_POS = "ticket_pos"
    TABLE = "table"
    FORM = "form"
    UNKNOWN = "unknown"


@dataclass
class OCRResult:
    """Resultado de OCR."""

    text: str
    pages: int
    layout: DocumentLayout
    confidence: float
    regions: list[dict[str, Any]] = field(default_factory=list)
    tables: list[list[list[str]]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    processing_time_ms: float = 0.0


class OCRService:
    """Servicio de OCR híbrido (PyMuPDF + Tesseract)."""

    SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"}

    def __init__(self) -> None:
        self.logger = logger
        self._fitz_available = False
        self._tesseract_available = False
        self._check_dependencies()

    def _check_dependencies(self) -> None:
        """Verifica que las dependencias estén instaladas."""
        try:
            import fitz  # noqa: F401

            self._fitz_available = True
        except ImportError:
            self.logger.warning("PyMuPDF (fitz) not available. PDF processing disabled.")

        try:
            import pytesseract

            pytesseract.get_tesseract_version()
            self._tesseract_available = True
        except Exception:
            self.logger.warning("Tesseract not available. OCR disabled.")

    def is_available(self) -> bool:
        """Retorna True si al menos un método de extracción está disponible."""
        return self._fitz_available or self._tesseract_available

    def supports_extension(self, file_path: str) -> bool:
        """Verifica si el archivo tiene una extensión soportada."""
        ext = Path(file_path).suffix.lower()
        return ext in self.SUPPORTED_EXTENSIONS

    async def extract_text(self, file_path: str) -> OCRResult:
        """
        Extrae texto de un archivo PDF o imagen.

        Estrategia:
        1. Si es PDF con texto embebido → extraer directamente (PyMuPDF)
        2. Si es PDF escaneado o imagen → OCR (Tesseract)
        3. Detectar tablas si hay estructura
        4. Clasificar layout del documento
        """
        start_time = time.perf_counter()
        ext = Path(file_path).suffix.lower()

        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {ext}")

        if ext == ".pdf":
            result = await self._process_pdf(file_path)
        else:
            result = await self._process_image(file_path)

        result.processing_time_ms = (time.perf_counter() - start_time) * 1000
        return result

    async def _process_pdf(self, file_path: str) -> OCRResult:
        """Procesa PDF (texto embebido o escaneado)."""
        if not self._fitz_available:
            raise RuntimeError("PyMuPDF not available for PDF processing")

        import fitz

        doc = fitz.open(file_path)
        text_parts: list[str] = []
        tables: list[list[list[str]]] = []
        regions: list[dict[str, Any]] = []
        has_embedded_text = False
        total_chars = 0

        try:
            for page_num, page in enumerate(doc):
                page_text = page.get_text()
                if page_text.strip():
                    total_chars += len(page_text.strip())
                    text_parts.append(page_text)

                page_tables = self._extract_tables_from_page(page)
                tables.extend(page_tables)

            has_embedded_text = total_chars > 50
            num_pages = len(doc)
        finally:
            doc.close()

        if not has_embedded_text:
            return await self._ocr_pdf(file_path)

        full_text = "\n".join(text_parts)
        layout = self._detect_layout(full_text, tables)

        return OCRResult(
            text=full_text,
            pages=num_pages,
            layout=layout,
            confidence=0.95,
            regions=regions,
            tables=tables,
            metadata={
                "source": "embedded",
                "has_tables": len(tables) > 0,
                "char_count": total_chars,
            },
        )

    async def _ocr_pdf(self, file_path: str) -> OCRResult:
        """OCR para PDF escaneado."""
        if not self._fitz_available:
            raise RuntimeError("PyMuPDF not available for PDF processing")
        if not self._tesseract_available:
            raise RuntimeError("Tesseract not available for OCR")

        import fitz
        import pytesseract
        from PIL import Image

        doc = fitz.open(file_path)
        text_parts: list[str] = []
        confidences: list[float] = []

        try:
            for page in doc:
                pix = page.get_pixmap(dpi=200)
                img = Image.open(io.BytesIO(pix.tobytes("png")))

                page_data = pytesseract.image_to_data(
                    img, lang="spa+eng", output_type=pytesseract.Output.DICT
                )

                page_text = pytesseract.image_to_string(img, lang="spa+eng")
                text_parts.append(page_text)

                page_confs = [
                    int(c) for c in page_data.get("conf", []) if str(c).isdigit() and int(c) > 0
                ]
                if page_confs:
                    confidences.append(sum(page_confs) / len(page_confs) / 100)

            num_pages = len(doc)
        finally:
            doc.close()

        full_text = "\n".join(text_parts)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.7
        layout = self._detect_layout(full_text, [])

        return OCRResult(
            text=full_text,
            pages=num_pages,
            layout=layout,
            confidence=min(avg_confidence, 0.85),
            regions=[],
            tables=[],
            metadata={
                "source": "ocr",
                "engine": "tesseract",
                "languages": ["spa", "eng"],
            },
        )

    async def _process_image(self, file_path: str) -> OCRResult:
        """Procesa imagen con OCR."""
        if not self._tesseract_available:
            raise RuntimeError("Tesseract not available for OCR")

        import pytesseract
        from PIL import Image

        img = Image.open(file_path)

        if img.mode != "RGB":
            img = img.convert("RGB")

        page_data = pytesseract.image_to_data(
            img, lang="spa+eng", output_type=pytesseract.Output.DICT
        )
        text = pytesseract.image_to_string(img, lang="spa+eng")

        confs = [int(c) for c in page_data.get("conf", []) if str(c).isdigit() and int(c) > 0]
        avg_confidence = sum(confs) / len(confs) / 100 if confs else 0.7

        regions = self._extract_regions_from_data(page_data)
        layout = self._detect_layout(text, [])

        return OCRResult(
            text=text,
            pages=1,
            layout=layout,
            confidence=min(avg_confidence, 0.85),
            regions=regions,
            tables=[],
            metadata={
                "source": "ocr",
                "engine": "tesseract",
                "languages": ["spa", "eng"],
                "image_size": img.size,
            },
        )

    def _detect_layout(self, text: str, tables: list) -> DocumentLayout:
        """Detecta el tipo de layout del documento."""
        text_lower = text.lower()

        ticket_pos_keywords = [
            "ticket de venta",
            "nº r-",
            "n° r-",
            "no r-",
            "ticket venta",
        ]
        ticket_pos_score = sum(1 for kw in ticket_pos_keywords if kw in text_lower)
        has_pos_line_format = bool(
            re.search(r"\d+[.,]?\d*\s*x\s+.+\s*[-–]\s*\$?\s*\d+[.,]\d{2}", text_lower)
        )
        if ticket_pos_score >= 1 or (has_pos_line_format and "total" in text_lower):
            return DocumentLayout.TICKET_POS

        invoice_keywords = [
            "factura",
            "invoice",
            "ruc",
            "nif",
            "iva",
            "tax",
            "subtotal",
            "cif",
            "nit",
        ]
        receipt_keywords = [
            "recibo",
            "receipt",
            "ticket",
            "total",
            "efectivo",
            "cash",
            "paid",
        ]
        bank_keywords = [
            "extracto",
            "statement",
            "saldo",
            "balance",
            "iban",
            "cuenta",
            "account",
            "movimientos",
        ]

        invoice_score = sum(1 for kw in invoice_keywords if kw in text_lower)
        receipt_score = sum(1 for kw in receipt_keywords if kw in text_lower)
        bank_score = sum(1 for kw in bank_keywords if kw in text_lower)

        if invoice_score >= 3:
            return DocumentLayout.INVOICE
        if receipt_score >= 3:
            return DocumentLayout.RECEIPT
        if bank_score >= 3:
            return DocumentLayout.BANK_STATEMENT
        if tables:
            return DocumentLayout.TABLE

        return DocumentLayout.UNKNOWN

    def _extract_tables_from_page(self, page: Any) -> list[list[list[str]]]:
        """Extrae tablas de una página PDF usando PyMuPDF."""
        tables: list[list[list[str]]] = []

        try:
            if hasattr(page, "find_tables"):
                found_tables = page.find_tables()
                for table in found_tables:
                    table_data = table.extract()
                    if table_data and len(table_data) > 1:
                        cleaned = [
                            [str(cell) if cell else "" for cell in row] for row in table_data
                        ]
                        tables.append(cleaned)
        except Exception as e:
            self.logger.debug(f"Table extraction failed: {e}")

        return tables

    def _extract_regions_from_data(self, data: dict) -> list[dict[str, Any]]:
        """Extrae regiones de texto con sus bounding boxes."""
        regions: list[dict[str, Any]] = []

        texts = data.get("text", [])
        lefts = data.get("left", [])
        tops = data.get("top", [])
        widths = data.get("width", [])
        heights = data.get("height", [])
        confs = data.get("conf", [])

        for i, text in enumerate(texts):
            if text and text.strip() and len(lefts) > i:
                conf = int(confs[i]) if str(confs[i]).isdigit() else 0
                if conf > 50:
                    regions.append(
                        {
                            "text": text.strip(),
                            "bbox": [lefts[i], tops[i], widths[i], heights[i]],
                            "confidence": conf / 100,
                        }
                    )

        return regions


ocr_service = OCRService()
