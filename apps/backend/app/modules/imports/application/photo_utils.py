"""Photo and OCR utilities for imports module."""

from __future__ import annotations

import hashlib
import logging
import os
import re
import tempfile
import time
import uuid
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from .ocr_config import get_ocr_config
from .security_config import get_security_config
from .security_guards import SecurityViolationError, validate_file_security

logger = logging.getLogger(__name__)

# Lazy imports to avoid import errors when deps not available
try:
    import cv2

    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    logger.warning("OpenCV not available - image preprocessing disabled")

try:
    import fitz  # PyMuPDF

    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF not available - PDF native text extraction disabled")

TESSERACT_AVAILABLE: bool | None = None
EASYOCR_AVAILABLE: bool | None = None
pytesseract = None
Image = None
easyocr = None

try:
    from pyzbar import pyzbar

    PYZBAR_AVAILABLE = True
except Exception:
    PYZBAR_AVAILABLE = False
    logger.warning("pyzbar unavailable or libzbar missing - QR code detection disabled")


# Cache for OCR results (in-memory)
_OCR_CACHE: dict[str, str] = {}
_QR_CACHE: dict[str, list[str]] = {}
_EASYOCR_READERS: dict[str, Any] = {}


def _ensure_tesseract() -> bool:
    global TESSERACT_AVAILABLE, pytesseract, Image
    if TESSERACT_AVAILABLE is not None:
        return TESSERACT_AVAILABLE
    if os.getenv("IMPORTS_TESSERACT_ENABLED", "1").lower() not in ("1", "true", "yes"):
        TESSERACT_AVAILABLE = False
        return False
    try:
        import pytesseract as _pytesseract
        from PIL import Image as _Image

        pytesseract = _pytesseract
        Image = _Image
        TESSERACT_AVAILABLE = True
    except ImportError:
        TESSERACT_AVAILABLE = False
        logger.warning("Tesseract not available - will try EasyOCR fallback")
    return TESSERACT_AVAILABLE


def _ensure_easyocr() -> bool:
    global EASYOCR_AVAILABLE, easyocr
    if EASYOCR_AVAILABLE is not None:
        return EASYOCR_AVAILABLE
    if os.getenv("IMPORTS_EASYOCR_ENABLED", "1").lower() not in ("1", "true", "yes"):
        EASYOCR_AVAILABLE = False
        return False
    try:
        import easyocr as _easyocr

        easyocr = _easyocr
        EASYOCR_AVAILABLE = True
    except ImportError:
        EASYOCR_AVAILABLE = False
        logger.warning("EasyOCR not available")
    return EASYOCR_AVAILABLE


def exif_auto_orienta(content: bytes) -> bytes:
    """Auto-rotate image based on EXIF orientation."""
    if not OPENCV_AVAILABLE:
        return content

    try:
        import numpy as np

        nparr = np.frombuffer(content, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return content

        # Simple rotation detection (basic implementation)
        # For full EXIF support, would need PIL/Pillow
        return content
    except Exception as e:
        logger.warning(f"EXIF orientation failed: {e}")
        return content


def guardar_adjunto_bytes(
    tenant_id: str | int, content: bytes, *, filename: str
) -> tuple[str, str]:
    """Persist attachment to local uploads folder and return (file_key, sha256)."""
    base_dir = os.path.join("uploads", "imports", str(tenant_id))
    os.makedirs(base_dir, exist_ok=True)
    ext = os.path.splitext(filename)[1] or ".bin"
    key = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(base_dir, key)
    with open(path, "wb") as f:
        f.write(content)
    sha = hashlib.sha256(content).hexdigest()
    file_key = f"imports/{tenant_id}/{key}"
    return file_key, sha


def detect_native_text_in_pdf(pdf_path: str, min_chars: int = 30) -> str | None:
    """
    Extract native text from PDF using PyMuPDF.
    Returns text if >= min_chars found, else None (indicating OCR needed).
    """
    if not PYMUPDF_AVAILABLE:
        return None

    config = get_ocr_config()
    if config.skip_native_pdf and "PYTEST_CURRENT_TEST" not in os.environ:
        return None

    try:
        start = time.time()
        doc = fitz.open(pdf_path)
        full_text = ""

        for page_num in range(min(len(doc), config.max_pages)):
            page = doc[page_num]
            text_page = page.get_text("text")
            if not text_page:
                try:
                    blocks = page.get_text("blocks")
                    text_page = " ".join(
                        block[4] for block in blocks if len(block) > 4 and block[4]
                    )
                except Exception:
                    text_page = ""
            full_text += text_page

        doc.close()
        elapsed = time.time() - start

        normalized = re.sub(r"\s+", " ", full_text).strip()
        if len(normalized) >= min_chars:
            logger.info(
                f"PDF native text extracted: {len(normalized)} chars in {elapsed:.2f}s, skipping OCR"
            )
            return normalized

        logger.info(f"PDF native text insufficient ({len(normalized)} chars), will use OCR")
        return None
    except Exception as e:
        logger.warning(f"PDF native text extraction failed: {e}")
        return None


def preprocess_image(img) -> Any:
    """
    Preprocess image for better OCR results using OpenCV.
    - Convert to grayscale
    - Deskew using minAreaRect
    - Denoise with fastNlMeansDenoising
    - Adaptive threshold
    """
    if not OPENCV_AVAILABLE:
        return img

    try:
        start = time.time()

        # Convert to grayscale
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img

        # Deskew
        coords = cv2.findNonZero(cv2.bitwise_not(gray))
        if coords is not None:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle

            if abs(angle) > 0.5:  # Only rotate if angle significant
                (h, w) = gray.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                gray = cv2.warpAffine(
                    gray,
                    M,
                    (w, h),
                    flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_REPLICATE,
                )

        # Denoise
        gray = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)

        # Adaptive threshold
        processed = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        elapsed = time.time() - start
        logger.debug(f"Image preprocessing completed in {elapsed:.3f}s")

        return processed
    except Exception as e:
        logger.warning(f"Image preprocessing failed: {e}, using original")
        return img


def extract_qr_codes(img) -> list[str]:
    """
    Extract QR codes from image using pyzbar.
    Returns list of decoded strings (e.g., SRI clave de acceso).
    """
    if not PYZBAR_AVAILABLE:
        return []

    try:
        start = time.time()
        qr_codes = pyzbar.decode(img)
        results = [qr.data.decode("utf-8") for qr in qr_codes if qr.data]
        elapsed = time.time() - start

        if results:
            logger.info(f"Extracted {len(results)} QR codes in {elapsed:.3f}s")

        return results
    except Exception as e:
        logger.warning(f"QR code extraction failed: {e}")
        return []


def extract_text_from_image(content: bytes, file_sha: str | None = None) -> str:
    """
    Extract text from image using OCR with preprocessing and caching.

    Args:
        content: Image bytes
        file_sha: Optional SHA256 hash for caching

    Returns:
        Extracted text
    """
    config = get_ocr_config()

    # Check cache
    if file_sha and config.enable_cache and file_sha in _OCR_CACHE:
        logger.debug(f"OCR cache hit for {file_sha[:8]}")
        return _OCR_CACHE[file_sha]

    start = time.time()
    text = ""

    try:
        import numpy as np

        # Decode image
        nparr = np.frombuffer(content, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR) if OPENCV_AVAILABLE else None

        if img is None:
            # Fallback to PIL
            if _ensure_tesseract():
                from io import BytesIO

                img = Image.open(BytesIO(content))

        # Extract QR codes first (may contain useful data)
        qr_codes = []
        if config.enable_qr and OPENCV_AVAILABLE and img is not None:
            qr_codes = extract_qr_codes(img)
            if file_sha and qr_codes:
                _QR_CACHE[file_sha] = qr_codes

        # Preprocess image
        if OPENCV_AVAILABLE and img is not None:
            img = preprocess_image(img)

        # Tesseract (preferred)
        if _ensure_tesseract():
            try:
                if OPENCV_AVAILABLE:
                    # Convert opencv image to PIL
                    from PIL import Image as PILImage

                    pil_img = PILImage.fromarray(img)
                else:
                    pil_img = img

                custom_config = f"--psm {config.ocr_psm} --dpi {config.ocr_dpi}"
                text = pytesseract.image_to_string(
                    pil_img, lang=config.ocr_lang, config=custom_config
                )
                logger.info(f"Tesseract OCR completed: {len(text)} chars")
            except Exception as e:
                logger.warning(f"Tesseract OCR failed: {e}, trying EasyOCR fallback")
                if _ensure_easyocr():
                    text = _easyocr_fallback(content)
        elif _ensure_easyocr():
            text = _easyocr_fallback(content)
        else:
            logger.error("No OCR engine available")

        # Add QR codes to text if found
        if qr_codes:
            text = "\n".join(qr_codes) + "\n" + text

        elapsed = time.time() - start
        logger.info(f"OCR completed in {elapsed:.2f}s: {len(text)} chars extracted")

        # Cache result
        if file_sha and config.enable_cache:
            _OCR_CACHE[file_sha] = text

    except Exception as e:
        logger.error(f"OCR failed: {e}")

    return text


def _get_easyocr_reader(easyocr_langs: list[str]) -> Any:
    """Get cached EasyOCR reader for given languages."""
    key = ",".join(sorted(easyocr_langs))
    if key not in _EASYOCR_READERS:
        logger.info(f"Initializing EasyOCR reader for languages: {easyocr_langs}")
        _EASYOCR_READERS[key] = easyocr.Reader(easyocr_langs, gpu=False)
    return _EASYOCR_READERS[key]


def _easyocr_fallback(content: bytes) -> str:
    """Fallback OCR using EasyOCR."""
    try:
        config = get_ocr_config()
        langs = config.ocr_lang.replace("+", " ").split()
        lang_map = {"spa": "es", "eng": "en"}
        easyocr_langs = [lang_map.get(lang, lang) for lang in langs]

        reader = _get_easyocr_reader(easyocr_langs)

        import numpy as np

        nparr = np.frombuffer(content, np.uint8)
        if OPENCV_AVAILABLE:
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        else:
            img = nparr

        results = reader.readtext(img)
        text = "\n".join([res[1] for res in results])
        logger.info(f"EasyOCR fallback completed: {len(text)} chars")
        return text
    except Exception as e:
        logger.error(f"EasyOCR fallback failed: {e}")
        return ""


def process_pdf_page(page_data: tuple[bytes, int, str]) -> str:
    """Process single PDF page for multiprocessing."""
    pdf_bytes, page_num, file_sha = page_data
    os.environ["OMP_THREAD_LIMIT"] = "1"  # Limit OpenMP threads in worker

    logger.info(f"Processing PDF page {page_num}")
    return extract_text_from_image(pdf_bytes, f"{file_sha}_p{page_num}")


def extract_text_from_pdf_multipage(pdf_path: str, file_sha: str | None = None) -> str:
    """
    Extract text from multi-page PDF with multiprocessing.
    First tries native text extraction, falls back to OCR if needed.
    """
    config = get_ocr_config()

    # Try native text first
    native_text = detect_native_text_in_pdf(pdf_path)
    if native_text:
        return native_text

    # OCR fallback with multiprocessing
    if not PYMUPDF_AVAILABLE:
        logger.error("PyMuPDF not available - PDF processing disabled")
        return ""

    try:
        start = time.time()
        if not file_sha:
            file_sha = hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest()

        doc = fitz.open(pdf_path)
        page_count = min(len(doc), config.max_pages)

        # Render pages to images
        page_data_list = []
        for page_num in range(page_count):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=config.ocr_dpi, colorspace=fitz.csGRAY)
            img_bytes = pix.tobytes("png")
            page_data_list.append((img_bytes, page_num, file_sha))

        doc.close()

        # Process pages in parallel
        if config.ocr_workers > 1 and page_count > 1:
            with ProcessPoolExecutor(max_workers=config.ocr_workers) as executor:
                results = list(executor.map(process_pdf_page, page_data_list))
        else:
            results = [process_pdf_page(pd) for pd in page_data_list]

        full_text = "\n\n".join(results)
        elapsed = time.time() - start

        logger.info(
            f"PDF OCR completed: {page_count} pages, {len(full_text)} chars "
            f"in {elapsed:.2f}s ({elapsed / page_count:.2f}s/page)"
        )

        return full_text
    except Exception as e:
        logger.error(f"PDF multipage OCR failed: {e}")
        return ""


def ocr_texto(content: bytes, filename: str = "") -> str:
    """
    Main OCR entry point - handles both images and PDFs.

    Args:
        content: File bytes
        filename: Optional filename to detect PDF

    Returns:
        Extracted text

    Raises:
        SecurityViolationError: If file fails security validation
    """
    file_sha = hashlib.sha256(content).hexdigest()

    # Security validation
    security_config = get_security_config()
    temp_path = None

    try:
        # Save to temp file for security checks
        is_pdf = filename.lower().endswith(".pdf") or content[:4] == b"%PDF"
        ext = ".pdf" if is_pdf else os.path.splitext(filename)[1] or ".bin"
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"ocr_temp_{file_sha}{ext}")

        with open(temp_path, "wb") as f:
            f.write(content)

        # Run security guards
        try:
            validation_result = validate_file_security(
                temp_path,
                allowed_mimes=security_config.allowed_mime_types,
                max_mb=security_config.max_file_size_mb,
                max_pdf_pages=security_config.max_pdf_pages,
                enable_av_scan=security_config.enable_av_scan,
                reject_pdf_with_js=security_config.reject_pdf_with_js,
                bypass=security_config.bypass_security,
            )

            logger.info(
                f"Security validation passed for {filename} "
                f"(hash: {file_sha[:8]}..., checks: {len(validation_result.get('checks_passed', []))})"
            )
        except SecurityViolationError as e:
            logger.error(
                f"Security validation failed for {filename}: {e.code} - {e.detail} "
                f"(hash: {file_sha})"
            )
            raise

        # Process based on file type
        if is_pdf:
            return extract_text_from_pdf_multipage(temp_path, file_sha)
        else:
            return extract_text_from_image(content, file_sha)

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as e:
                logger.warning(f"Failed to clean up temp file {temp_path}: {e}")


# Naive parsers from text to normalized dicts (unchanged) --------------------


def _find_date(text: str) -> str | None:
    """Find date in text (ISO or dd/mm/yyyy format)."""
    m = re.search(r"\b\d{4}-\d{2}-\d{2}\b", text)
    if m:
        return m.group(0)
    m = re.search(r"\b\d{2}[/-]\d{2}[/-]\d{4}\b", text)
    if m:
        return m.group(0)
    return None


def _find_amount(text: str) -> float | None:
    """Find monetary amount in text."""
    m = re.search(r"-?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})", text)
    if not m:
        return None
    s = m.group(0).replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None


def parse_texto_factura(text: str) -> dict[str, Any]:
    """Parse invoice text to normalized dict."""
    inv = None
    m = re.search(
        r"(Invoice|Factura)\s*(Number|N[oº]?)?[:\-]?\s*([A-Za-z0-9\-/]+)",
        text,
        re.IGNORECASE,
    )
    if m:
        inv = m.group(3)
    return {
        "invoice_number": inv,
        "invoice_date": _find_date(text),
        "total_amount": _find_amount(text),
    }


def parse_texto_banco(text: str) -> dict[str, Any]:
    """Parse bank transaction text to normalized dict."""
    return {
        "transaction_date": _find_date(text),
        "amount": _find_amount(text),
        "description": (text[:120] if text else None),
    }


def parse_texto_recibo(text: str) -> dict[str, Any]:
    """Parse receipt text to normalized dict."""
    return {
        "expense_date": _find_date(text),
        "amount": _find_amount(text),
        "description": (text[:120] if text else None),
    }
