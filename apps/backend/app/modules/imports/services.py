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
from app.modules.imports.extractores.extractor_desconocido import extract_by_combined_types
from app.modules.imports.extractores.extractor_factura import extract_invoice
from app.modules.imports.extractores.extractor_recibo import extract_receipt
from app.modules.imports.extractores.extractor_transferencia import extract_transfers
from app.modules.imports.extractores.utilidades import detect_document_type
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


def _safe_float(v) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        try:
            return float(v)
        except Exception:
            return None
    s = str(v).strip()
    if not s:
        return None
    s = re.sub(r"[^0-9,.\-]", "", s)
    if not s:
        return None
    last_dot = s.rfind(".")
    last_comma = s.rfind(",")
    decimal_sep = "," if last_comma > last_dot else "."
    if decimal_sep == ",":
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")
    try:
        return float(s)
    except Exception:
        return None


def _is_empty_doc(doc: object) -> bool:
    """True if doc has no useful fields (all None/empty/zero-ish)."""
    if isinstance(doc, DocumentoProcesado):
        data = doc.model_dump()
    elif isinstance(doc, dict):
        data = doc
    else:
        return False
    vals = [
        data.get("tipo"),
        data.get("importe"),
        data.get("cliente"),
        data.get("invoice"),
        data.get("fecha"),
        data.get("cuenta"),
        data.get("concepto"),
        data.get("categoria"),
        data.get("origen"),
        data.get("documentoTipo"),
    ]
    if all(v is None or (isinstance(v, str) and not v.strip()) for v in vals):
        return True
    try:
        imp = data.get("importe")
        if imp is not None and float(imp) != 0:
            return False
    except Exception:
        pass
    # If only a date exists but everything else is empty, treat it as empty (frontend was defaulting to "today").
    fecha = data.get("fecha")
    if fecha and isinstance(fecha, str) and fecha.strip():
        others = [v for v in vals if v is not fecha]
        if all(v is None or (isinstance(v, str) and not v.strip()) for v in others):
            return True
    return False


def _canonical_to_documento_procesado(c: dict) -> DocumentoProcesado:
    doc_type = (c.get("doc_type") or c.get("documentoTipo") or c.get("tipo") or "").strip()
    totals = c.get("totals") or {}
    lines = c.get("lines") or []
    first_line = lines[0] if isinstance(lines, list) and lines else {}
    routing = c.get("routing_proposal") or {}
    vendor = c.get("vendor") or {}
    buyer = c.get("buyer") or {}

    issue_date = (
        c.get("issue_date") or c.get("invoice_date") or c.get("expense_date") or c.get("value_date")
    )
    total_val = None
    if isinstance(totals, dict):
        total_val = totals.get("total")
    if total_val is None:
        total_val = c.get("total") or c.get("amount")
    if total_val is None and isinstance(first_line, dict):
        total_val = first_line.get("total") or first_line.get("unit_price")

    concepto = None
    if isinstance(first_line, dict):
        concepto = first_line.get("desc")
    concepto = concepto or c.get("description") or c.get("concept") or doc_type or "Documento OCR"

    cliente = None
    if isinstance(vendor, dict):
        cliente = vendor.get("name")
    if not cliente and isinstance(buyer, dict):
        cliente = buyer.get("name")

    cuenta = None
    if isinstance(routing, dict):
        cuenta = routing.get("account")

    categoria = None
    if isinstance(routing, dict):
        categoria = routing.get("category_code")

    invoice = c.get("invoice_number") or c.get("invoice")

    # Map to legacy-ish tipo values used by UI/pipeline.
    tipo = "expense"
    if doc_type == "bank_tx":
        # Try to infer from direction if present.
        bank_tx = c.get("bank_tx") or {}
        direction = None
        if isinstance(bank_tx, dict):
            direction = bank_tx.get("direction")
        if direction == "credit":
            tipo = "income"
        elif direction == "debit":
            tipo = "expense"

    return DocumentoProcesado(
        tipo=tipo,
        importe=_safe_float(total_val),
        cliente=str(cliente) if cliente is not None else None,
        invoice=str(invoice) if invoice is not None else None,
        fecha=str(issue_date) if issue_date is not None else None,
        cuenta=str(cuenta) if cuenta is not None else None,
        concepto=str(concepto) if concepto is not None else None,
        categoria=str(categoria) if categoria is not None else None,
        origen=str(c.get("source") or c.get("origen") or "ocr"),
        documentoTipo=doc_type or None,
    )


def _to_documento_procesado(doc: object) -> DocumentoProcesado | None:
    if doc is None:
        return None
    if isinstance(doc, DocumentoProcesado):
        return None if _is_empty_doc(doc) else doc
    if isinstance(doc, dict):
        # Canonical schema?
        if "doc_type" in doc or "totals" in doc or "lines" in doc:
            out = _canonical_to_documento_procesado(doc)
            return None if _is_empty_doc(out) else out
        try:
            out = DocumentoProcesado(**doc)
            return None if _is_empty_doc(out) else out
        except Exception:
            return None
    return None


try:  # eager warm-up (desactivado por defecto en prod)
    if bool(getattr(settings, "IMPORTS_EASYOCR_WARM_ON_START", False)):
        _get_easyocr_reader()  # noqa: F821
except Exception:  # nosec B110
    # best-effort; on failure the reader will be lazily retried later
    pass


def _get_easyocr_reader() -> object | None:
    global _easyocr_reader
    if _easyocr_reader is not None:
        return _easyocr_reader
    # flag por configuración
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


def limpiar_texto_ocr(texto: str) -> str:
    # Quita caracteres no imprimibles, pero conserva acentos y ñ
    texto = re.sub(r"[^\x09\x0A\x0D\x20-\x7EáéíóúÁÉÍÓÚñÑüÜ.,;:¡!¿?()\[\]{}]", "", texto)
    # Reemplaza caracteres de error típicos
    texto = texto.replace("�", "").replace("·", ".").replace(""", '"').replace(""", '"')
    return texto


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


def _tesseract_psm_from_env(default: int = 6) -> int:
    try:
        return int(os.getenv("IMPORTS_OCR_PSM", str(default)))
    except Exception:
        return default


def _tesseract_dpi_from_env(default: int = 300) -> int:
    try:
        return int(os.getenv("IMPORTS_OCR_DPI", str(default)))
    except Exception:
        return default


def _ocr_texto_desde_imagen_path(img_path: str) -> str:
    texto = ""
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
                try:
                    from PIL import ImageEnhance, ImageOps

                    image = ImageOps.exif_transpose(image)
                    image = image.convert("L")
                    image = ImageOps.autocontrast(image)
                    image = ImageEnhance.Sharpness(image).enhance(1.5)
                    w, h = image.size
                    if max(w, h) < 2000:
                        image = image.resize((w * 2, h * 2))
                except Exception:
                    pass

                langs = _tesseract_langs_from_settings()
                dpi = _tesseract_dpi_from_env(300)
                psm0 = _tesseract_psm_from_env(6)
                best = ""
                seen: set[int] = set()
                for psm in (psm0, 4, 6, 11):
                    if psm in seen:
                        continue
                    seen.add(psm)
                    cfg = f"--psm {psm} --dpi {dpi}"
                    cand = _pytesseract.image_to_string(image, lang=langs, config=cfg) or ""
                    if len(cand) > len(best):
                        best = cand
                    if len(best.strip()) >= 200:
                        break
                texto = best
            except Exception:
                texto = ""
    if not texto and _get_easyocr_reader() is not None:
        try:
            reader = _get_easyocr_reader()
            assert reader is not None
            ocr_result = reader.readtext(img_path, detail=0, paragraph=True)  # type: ignore[attr-defined]
            texto = " ".join(ocr_result)
        except Exception:
            texto = ""
    return limpiar_texto_ocr(texto.strip()) if texto else ""


def extraer_texto_ocr_hibrido_paginas(file_bytes: bytes, filename: str | None = None) -> list[str]:
    """Extrae texto por página intentando Tesseract y fallback a EasyOCR.

    - Si falta PyMuPDF/Pillow/Tesseract/EasyOCR, se degrada sin romper.
    - Devuelve lista de strings (una por página) ya limpiados.
    """
    paginas: list[str] = []
    lower_name = (filename or "").lower()
    is_pdf = lower_name.endswith(".pdf") or file_bytes[:5] == b"%PDF-"

    if not is_pdf:
        suffix = Path(filename).suffix if filename else ".img"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix or ".img") as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        try:
            text_image = _ocr_texto_desde_imagen_path(tmp_path)
            if text_image:
                paginas.append(text_image)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
        return [t for t in paginas if t]

    # Lazy import fitz (PyMuPDF) to avoid heavy import at startup
    if fitz is None:
        try:
            fitz_mod = importlib.import_module("fitz")  # type: ignore
            globals()["fitz"] = fitz_mod
        except Exception:  # nosec B110
            pass

    if fitz is None:  # no PDF rasterizer available
        return paginas  # devolver vacío; el caller manejará fallback

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        doc = fitz.open(tmp_path)
        for page in doc:
            # 0) Intento rápido: extraer texto vectorial sin OCR
            try:
                text_direct = page.get_text("text") or ""
            except Exception:
                text_direct = ""

            if text_direct and text_direct.strip():
                paginas.append(limpiar_texto_ocr(text_direct.strip()))
                continue

            # 1) Rasterizar la página y aplicar OCR
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
                        # psm 6: assume a uniform block of text; works well for facturas/recibos
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
                paginas.append(limpiar_texto_ocr(text_page.strip()))

            Path(img_path).unlink(missing_ok=True)
        try:
            doc.close()
        except Exception:  # nosec B110
            pass
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return [t for t in paginas if t]


def _normalizar_tipo_por_importe(doc: DocumentoProcesado) -> DocumentoProcesado:
    """Unifies type heuristic: positive amounts default to expenses.

    If an extractor already defines `type`, respects it; otherwise uses: amount >= 0 -> "expense" else "income".
    """
    if getattr(doc, "tipo", None) in ("income", "expense"):
        return doc
    try:
        return doc.copy(update={"tipo": "expense" if float(doc.importe or 0) >= 0 else "income"})
    except Exception:
        return doc


def _resolver_tipo_documento(texto_total: str) -> str:
    t = (texto_total or "").lower()
    # Heurística fuerte para factura fiscal (EC/ES)
    if (
        "factura" in t
        or "ruc" in t
        or "numero autorizacion" in t
        or "fecha de emision" in t
        or "subtotal" in t
    ):
        return "factura"
    detected = detect_document_type(texto_total)
    aliases = {
        "invoice": "factura",
        "transfer": "transferencia",
        "receipt": "recibo",
        "pos_ticket": "ticket_pos",
        "unknown": "desconocido",
    }
    return aliases.get(str(detected), str(detected))


def procesar_documento(file_bytes: bytes, filename: str) -> list[DocumentoProcesado]:
    paginas_ocr = extraer_texto_ocr_hibrido_paginas(file_bytes, filename)
    if not paginas_ocr:  # fallback si no pudimos rasterizar el PDF
        return []

    texto_total = " ".join(paginas_ocr)
    tipo = _resolver_tipo_documento(texto_total)
    # Debug opcional: dejar descomentado solo en desarrollo
    # print("📄 Tipo detectado:", tipo)

    from app.modules.imports.extractores.extractor_ticket import extraer_ticket_documentos

    extractor_map: dict[str, Callable[[str], list[DocumentoProcesado]]] = {
        "factura": extract_invoice,
        "recibo": extract_receipt,
        "transferencia": extract_transfers,
        "bancario": extract_transfers,
        "ticket_pos": extraer_ticket_documentos,
        "desconocido": extract_by_combined_types,
    }

    extractor = extractor_map.get(tipo, extract_by_combined_types)
    resultados: list[DocumentoProcesado] = []
    for pagina_texto in paginas_ocr:
        try:
            documentos = extractor(pagina_texto)
            if not documentos and extractor is not extract_by_combined_types:
                # Fallback when specific extractor fails for noisy OCR text.
                documentos = extract_by_combined_types(pagina_texto)
            converted: list[DocumentoProcesado] = []
            for d in documentos or []:
                dp = _to_documento_procesado(d)
                if dp is not None:
                    converted.append(dp)
            # If extractor produced only empty/invalid docs, fallback to combined types once.
            if not converted and extractor is not extract_by_combined_types:
                try:
                    documentos2 = extract_by_combined_types(pagina_texto)
                    for d in documentos2 or []:
                        dp = _to_documento_procesado(d)
                        if dp is not None:
                            converted.append(dp)
                except Exception:
                    converted = []
            resultados.extend(converted)
        except Exception:  # nosec B112
            try:
                documentos2 = extract_by_combined_types(pagina_texto)
                for d in documentos2 or []:
                    dp = _to_documento_procesado(d)
                    if dp is not None:
                        resultados.append(dp)
            except Exception:
                continue

    # Normalización de tipo
    return [_normalizar_tipo_por_importe(d) for d in resultados]
