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

from app.modules.imports.config.classification import get_classification_keywords
from app.modules.imports.application.ocr_config import get_ocr_config

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
        self._deps_checked = False
        self._config = None

    def _get_config(self):
        """Load OCR config from environment (cached per process)."""
        if self._config is None:
            self._config = get_ocr_config()
        return self._config

    @staticmethod
    def _parse_langs(lang_str: str) -> list[str]:
        """Split tesseract lang string like 'spa+eng' into list."""
        return [lang for lang in re.split(r"[+,\s]+", lang_str) if lang]

    @staticmethod
    def _build_text_from_tesseract_data(data: dict[str, Any]) -> str:
        """Reconstruct ordered text from pytesseract.image_to_data output."""
        if not data:
            return ""

        lines: dict[tuple[int, int], list[tuple[int, str]]] = {}
        texts = data.get("text", [])
        confs = data.get("conf", [])
        blocks = data.get("block_num", [])
        line_nums = data.get("line_num", [])
        lefts = data.get("left", [])

        for idx, word in enumerate(texts):
            if not word or str(confs[idx]).strip() in ("", "-1"):
                continue
            block = blocks[idx] if idx < len(blocks) else 0
            line = line_nums[idx] if idx < len(line_nums) else 0
            left = lefts[idx] if idx < len(lefts) else idx
            lines.setdefault((block, line), []).append((left, word))

        ordered_lines = []
        for (block, line), words in sorted(lines.items(), key=lambda x: (x[0][0], x[0][1])):
            ordered_words = [w for _, w in sorted(words, key=lambda p: p[0])]
            ordered_lines.append(" ".join(ordered_words))

        return "\n".join(ordered_lines)

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

    def _ensure_dependencies(self) -> None:
        if not self._deps_checked:
            self._check_dependencies()
            self._deps_checked = True

    def is_available(self) -> bool:
        """Retorna True si al menos un método de extracción está disponible."""
        self._ensure_dependencies()
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
        self._ensure_dependencies()
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
        self._ensure_dependencies()
        if not self._fitz_available:
            raise RuntimeError("PyMuPDF not available for PDF processing")
        if not self._tesseract_available:
            raise RuntimeError("Tesseract not available for OCR")

        import fitz
        import pytesseract
        from PIL import Image

        cfg = self._get_config()
        doc = fitz.open(file_path)
        text_parts: list[str] = []
        confidences: list[float] = []
        dpi = max(cfg.ocr_dpi, 300)
        ocr_config = f"--psm {cfg.ocr_psm} --oem 1 -c preserve_interword_spaces=1"

        try:
            for page in doc:
                pix = page.get_pixmap(dpi=dpi)
                img = Image.open(io.BytesIO(pix.tobytes("png")))

                page_data = pytesseract.image_to_data(
                    img,
                    lang=cfg.ocr_lang,
                    config=ocr_config,
                    output_type=pytesseract.Output.DICT,
                )

                page_text = self._build_text_from_tesseract_data(page_data)
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
                "languages": self._parse_langs(cfg.ocr_lang),
                "psm": cfg.ocr_psm,
                "dpi": dpi,
            },
        )

    async def _process_image(self, file_path: str) -> OCRResult:
        """Procesa imagen con OCR."""
        self._ensure_dependencies()
        if not self._tesseract_available:
            raise RuntimeError("Tesseract not available for OCR")

        import pytesseract
        from PIL import Image

        cfg = self._get_config()
        img = Image.open(file_path)

        if img.mode != "RGB":
            img = img.convert("RGB")

        ocr_config = f"--psm {cfg.ocr_psm} --oem 1 -c preserve_interword_spaces=1"

        page_data = pytesseract.image_to_data(
            img,
            lang=cfg.ocr_lang,
            config=ocr_config,
            output_type=pytesseract.Output.DICT,
        )
        text = self._build_text_from_tesseract_data(page_data)

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
                "languages": self._parse_langs(cfg.ocr_lang),
                "psm": cfg.ocr_psm,
                "image_size": img.size,
            },
        )

    def _detect_layout(self, text: str, tables: list) -> DocumentLayout:
        """Detecta el tipo de layout del documento."""
        text_lower = text.lower()

        ticket_pos_keywords = [
            "ticket de venta",
            "ticket venta",
            "nº r-",
            "n° r-",
            "no r-",
            "nã° r-",
            "n\u00ba r-",
            "comprobante de venta",
            "nota de venta",
            "boleta de venta",
        ]
        ticket_pos_score = sum(1 for kw in ticket_pos_keywords if kw in text_lower)
        has_pos_line_format = bool(re.search(r"\d+[.,]?\d*\s*x\s+.+", text_lower))
        is_short_doc = len(text_lower) < 1500
        has_gracias = "gracias" in text_lower or "thank" in text_lower

        if ticket_pos_score >= 1:
            return DocumentLayout.TICKET_POS
        if has_pos_line_format and "total" in text_lower:
            return DocumentLayout.TICKET_POS
        if is_short_doc and has_gracias and "total" in text_lower:
            return DocumentLayout.TICKET_POS

        invoice_keywords = list(get_classification_keywords("invoices"))
        if not invoice_keywords:
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
        receipt_keywords = list(get_classification_keywords("expenses"))
        if not receipt_keywords:
            receipt_keywords = ["recibo", "receipt", "ticket", "total", "efectivo", "cash", "paid"]
        # Add receipt-specific keywords not in expenses category
        for kw in ["ticket", "total", "efectivo", "cash", "paid"]:
            if kw not in receipt_keywords:
                receipt_keywords.append(kw)
        bank_keywords = list(get_classification_keywords("bank_transactions"))
        if not bank_keywords:
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
        # Add bank-specific keywords
        for kw in ["extracto", "statement", "balance", "movimientos"]:
            if kw not in bank_keywords:
                bank_keywords.append(kw)

        invoice_score = sum(1 for kw in invoice_keywords if kw in text_lower)
        receipt_score = sum(1 for kw in receipt_keywords if kw in text_lower)
        bank_score = sum(1 for kw in bank_keywords if kw in text_lower)

        if invoice_score >= 3 and receipt_score >= 3:
            if is_short_doc or has_gracias or "cash" in text_lower or "paid" in text_lower:
                return DocumentLayout.RECEIPT

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
