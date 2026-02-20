"""Resilient OCR pipeline and document extraction services for Imports.

- Fully lazy-load OCR backends to avoid heavy init at import time.
- Graceful degradation if libraries are missing.
- Normalization helpers to keep downstream consistent.
"""

import importlib
import os
import re
import tempfile
from collections.abc import Callable
from pathlib import Path

from app.config.settings import settings
from app.modules.imports.extractors.extractor_invoice import extract_invoice
from app.modules.imports.extractors.extractor_receipt import extract_receipt
from app.modules.imports.extractors.extractor_transfer import extract_transfers
from app.modules.imports.extractors.extractor_unknown import extract_by_combined_types
from app.modules.imports.extractors.utilities import detect_document_type
from app.modules.imports.schemas import DocumentoProcesado

_SERVICES_EXTRA_PATH = Path(__file__).parent / "services"
# Allow `app.modules.imports.services.classifier` to load from the sibling directory.
if _SERVICES_EXTRA_PATH.is_dir():
    __path__ = [str(_SERVICES_EXTRA_PATH)]

fitz = None  # type: ignore
easyocr = None  # type: ignore
Image = None  # type: ignore
pytesseract = None  # type: ignore


_easyocr_reader: object | None = None


try:  # eager warm-up (disabled by default in prod)
    if bool(getattr(settings, "IMPORTS_EASYOCR_WARM_ON_START", False)):
        _get_easyocr_reader()  # noqa: F821
except Exception:  # nosec B110
    # best-effort; on failure the reader will be lazily retried later
    pass


def _get_easyocr_reader() -> object | None:
    global _easyocr_reader
    if _easyocr_reader is not None:
        return _easyocr_reader
    # configuration flag
    if not bool(getattr(settings, "IMPORTS_EASYOCR_ENABLED", True)):
        return None
    try:
        if easyocr is None:  # noqa: F823
            easyocr = importlib.import_module("easyocr")  # type: ignore
    except Exception:
        return None
    try:
        langs = getattr(settings, "IMPORTS_OCR_LANGS", ["es", "en"]) or ["es", "en"]
        _easyocr_reader = easyocr.Reader(langs, gpu=False)
        return _easyocr_reader
    except Exception:
        return None


def clean_ocr_text(text: str) -> str:
    # Remove non-printable characters, but preserve accents and ñ
    text = re.sub(r"[^\x09\x0A\x0D\x20-\x7EáéíóúÁÉÍÓÚñÑüÜ.,;:¡!¿?()\[\]{}]", "", text)
    # Replace typical error characters
    text = text.replace("�", "").replace("·", ".").replace(""", '"').replace(""", '"')
    return text


def _tesseract_langs_from_settings() -> str:
    ocr_lang = os.getenv("IMPORTS_OCR_LANG", "").strip()
    if ocr_lang:
        return ocr_lang
    raw = getattr(settings, "IMPORTS_OCR_LANGS", ["es", "en"]) or ["es", "en"]
    mapped: list[str] = []
    for lang in raw:
        token = str(lang).strip().lower()
        if token in ("es", "spa"):
            mapped.append("spa")
        elif token in ("en", "eng"):
            mapped.append("eng")
        elif token:
            mapped.append(token)
    return "+".join(mapped) if mapped else "spa+eng"


def _ocr_text_from_image_path(img_path: str) -> str:
    text = ""
    if bool(getattr(settings, "IMPORTS_TESSERACT_ENABLED", True)):
        try:
            _Image = importlib.import_module("PIL.Image")  # type: ignore
            _pytesseract = importlib.import_module("pytesseract")  # type: ignore
        except Exception:
            _Image = None  # type: ignore
            _pytesseract = None  # type: ignore
        if _Image is not None and _pytesseract is not None:
            try:
                tesseract_cmd = os.getenv("IMPORTS_TESSERACT_CMD", "").strip()
                if tesseract_cmd:
                    _pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
                image = _Image.open(img_path)  # type: ignore[attr-defined]
                langs = _tesseract_langs_from_settings()
                text = (
                    _pytesseract.image_to_string(
                        image,
                        lang=langs,
                        config="--psm 6",
                    )
                    or ""
                )  # type: ignore[attr-defined]
            except Exception:
                text = ""
    if not text and _get_easyocr_reader() is not None:
        try:
            reader = _get_easyocr_reader()
            assert reader is not None
            ocr_result = reader.readtext(img_path, detail=0, paragraph=True)  # type: ignore[attr-defined]
            text = " ".join(ocr_result)
        except Exception:
            text = ""
    return clean_ocr_text(text.strip()) if text else ""


def extract_ocr_text_hybrid_pages(file_bytes: bytes, filename: str | None = None) -> list[str]:
    """Extracts text by page attempting Tesseract and fallback to EasyOCR.

    - If PyMuPDF/Pillow/Tesseract/EasyOCR is missing, degrades without breaking.
    - Returns list of strings (one per page) already cleaned.
    """
    pages: list[str] = []
    lower_name = (filename or "").lower()
    is_pdf = lower_name.endswith(".pdf") or file_bytes[:5] == b"%PDF-"

    if not is_pdf:
        suffix = Path(filename).suffix if filename else ".img"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix or ".img") as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        try:
            image_text = _ocr_text_from_image_path(tmp_path)
            if image_text:
                pages.append(image_text)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
        return [t for t in pages if t]

    # Lazy import fitz (PyMuPDF) to avoid heavy import at startup
    if fitz is None:
        try:
            fitz_mod = importlib.import_module("fitz")  # type: ignore
            globals()["fitz"] = fitz_mod
        except Exception:  # nosec B110
            pass

    if fitz is None:  # no PDF rasterizer available
        return pages  # return empty; caller will handle fallback

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        doc = fitz.open(tmp_path)
        for page in doc:
            # 0) Quick attempt: extract vector text without OCR
            try:
                text_direct = page.get_text("text") or ""
            except Exception:
                text_direct = ""

            if text_direct and text_direct.strip():
                pages.append(clean_ocr_text(text_direct.strip()))
                continue

            # 1) Rasterize page and apply OCR
            try:
                pix = page.get_pixmap(dpi=300)
                img_path = f"{tmp_path}_p{page.number}.png"
                pix.save(img_path)
            except Exception:  # nosec B112
                continue

            text_page = ""
            # 1) Tesseract (configurable) with lazy import
            if bool(getattr(settings, "IMPORTS_TESSERACT_ENABLED", True)):
                try:
                    _Image = importlib.import_module("PIL.Image")  # type: ignore
                    _pytesseract = importlib.import_module("pytesseract")  # type: ignore
                except Exception:
                    _Image = None  # type: ignore
                    _pytesseract = None  # type: ignore
                if _Image is not None and _pytesseract is not None:
                    try:
                        tesseract_cmd = os.getenv("IMPORTS_TESSERACT_CMD", "").strip()
                        if tesseract_cmd:
                            _pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
                        image = _Image.open(img_path)  # type: ignore[attr-defined]
                        langs = _tesseract_langs_from_settings()
                        # psm 6: assume a uniform block of text; works well for invoices/receipts
                        text_page = (
                            _pytesseract.image_to_string(
                                image,
                                lang=langs,
                                config="--psm 6",
                            )
                            or ""
                        )  # type: ignore[attr-defined]
                    except Exception:
                        text_page = ""

            # 2) EasyOCR fallback
            if not text_page and _get_easyocr_reader() is not None:
                try:
                    reader = _get_easyocr_reader()
                    assert reader is not None
                    ocr_result = reader.readtext(img_path, detail=0, paragraph=True)  # type: ignore[attr-defined]
                    text_page = " ".join(ocr_result)
                except Exception:
                    text_page = ""

            if text_page:
                pages.append(clean_ocr_text(text_page.strip()))

            Path(img_path).unlink(missing_ok=True)
        try:
            doc.close()
        except Exception:  # nosec B110
            pass
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return [t for t in pages if t]


def _normalize_type_by_amount(doc: DocumentoProcesado) -> DocumentoProcesado:
    """Unifies type heuristic: positive amounts default to expenses.

    If an extractor already defines `type`, respects it; otherwise uses: amount >= 0 -> "expense" else "income".
    """
    if getattr(doc, "tipo", None) in ("income", "expense"):
        return doc
    try:
        return doc.copy(update={"tipo": "expense" if float(doc.importe or 0) >= 0 else "income"})
    except Exception:
        return doc


def _resolve_document_type(total_text: str) -> str:
    t = (total_text or "").lower()
    # Strong heuristic for fiscal invoice docs (EC/ES)
    if (
        "factura" in t
        or "ruc" in t
        or "numero autorizacion" in t
        or "fecha de emision" in t
        or "subtotal" in t
    ):
        return "invoice"
    detected = detect_document_type(total_text)
    return str(detected)


def process_document(file_bytes: bytes, filename: str) -> list[DocumentoProcesado]:
    pages_ocr = extract_ocr_text_hybrid_pages(file_bytes, filename)
    if not pages_ocr:  # fallback if we couldn't rasterize the PDF
        return []

    total_text = " ".join(pages_ocr)
    document_type = _resolve_document_type(total_text)
    # Optional debug: uncomment only in development
    # print("Document type detected:", document_type)

    from app.modules.imports.extractors.extractor_ticket import extract_ticket_documents

    extractor_map: dict[str, Callable[[str], list[DocumentoProcesado]]] = {
        "invoice": extract_invoice,
        "receipt": extract_receipt,
        "transfer": extract_transfers,
        "bancario": extract_transfers,
        "pos_ticket": extract_ticket_documents,
        "unknown": extract_by_combined_types,
    }

    extractor = extractor_map.get(document_type, extract_by_combined_types)
    results: list[DocumentoProcesado] = []
    for page_text in pages_ocr:
        try:
            documents = extractor(page_text)
            if not documents and extractor is not extract_by_combined_types:
                # Fallback when specific extractor fails for noisy OCR text.
                documents = extract_by_combined_types(page_text)
            results.extend(documents)
        except Exception:  # nosec B112
            try:
                results.extend(extract_by_combined_types(page_text))
            except Exception:
                continue

    # Type normalization
    return [_normalize_type_by_amount(d) for d in results]
