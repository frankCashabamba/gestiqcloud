"""Resilient OCR pipeline and document extraction services for Imports.

- Fully lazy-load OCR backends to avoid heavy init at import time.
- Graceful degradation if libraries are missing.
- Normalization helpers to keep downstream consistent.
"""

import importlib
import re
import tempfile
from pathlib import Path
from typing import Callable, List, Optional


_SERVICES_EXTRA_PATH = Path(__file__).parent / "services"
# Allow `app.modules.imports.services.classifier` to load from the sibling directory.
if _SERVICES_EXTRA_PATH.is_dir():
    __path__ = [str(_SERVICES_EXTRA_PATH)]

from app.modules.imports.schemas import DocumentoProcesado
from app.config.settings import settings
from app.modules.imports.extractores.extractor_desconocido import (
    extraer_por_tipos_combinados,
)
from app.modules.imports.extractores.extractor_factura import extraer_factura
from app.modules.imports.extractores.extractor_recibo import extraer_recibo
from app.modules.imports.extractores.extractor_transferencia import (
    extraer_transferencias,
)
from app.modules.imports.extractores.utilidades import detectar_tipo_documento

fitz = None  # type: ignore
easyocr = None  # type: ignore
Image = None  # type: ignore
pytesseract = None  # type: ignore


_easyocr_reader: Optional[object] = None


try:  # eager warm-up (desactivado por defecto en prod)
    if bool(getattr(settings, "IMPORTS_EASYOCR_WARM_ON_START", False)):
        _get_easyocr_reader()  # noqa: F821
except Exception:
    # best-effort; on failure the reader will be lazily retried later
    pass


def _get_easyocr_reader() -> Optional[object]:
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
    texto = texto.replace("�", "").replace("·", ".").replace("“", '"').replace("”", '"')
    return texto


def extraer_texto_ocr_hibrido_paginas(file_bytes: bytes) -> List[str]:
    """Extrae texto por página intentando Tesseract y fallback a EasyOCR.

    - Si falta PyMuPDF/Pillow/Tesseract/EasyOCR, se degrada sin romper.
    - Devuelve lista de strings (una por página) ya limpiados.
    """
    paginas: List[str] = []

    # Lazy import fitz (PyMuPDF) to avoid heavy import at startup
    if fitz is None:
        try:
            fitz_mod = importlib.import_module("fitz")  # type: ignore
            globals()["fitz"] = fitz_mod
        except Exception:
            pass

    if fitz is None:  # no PDF rasterizer available
        return paginas  # devolver vacío; el caller manejará fallback

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        doc = fitz.open(tmp_path)
        for page in doc:
            try:
                pix = page.get_pixmap(dpi=300)
                img_path = f"{tmp_path}_p{page.number}.png"
                pix.save(img_path)
            except Exception:
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
                        image = _Image.open(img_path)  # type: ignore[attr-defined]
                        text_page = (
                            _pytesseract.image_to_string(image, lang="eng") or ""
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
        except Exception:
            pass
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return [t for t in paginas if t]


def _normalizar_tipo_por_importe(doc: DocumentoProcesado) -> DocumentoProcesado:
    """Unifica la heurística de tipo: por defecto gastos positivos.

    Si un extractor ya define `tipo`, lo respeta; si no, usa: importe >= 0 -> "gasto" else "ingreso".
    """
    if getattr(doc, "tipo", None) in ("ingreso", "gasto"):
        return doc
    try:
        return doc.copy(
            update={"tipo": "gasto" if float(doc.importe or 0) >= 0 else "ingreso"}
        )
    except Exception:
        return doc


def procesar_documento(file_bytes: bytes, filename: str) -> List[DocumentoProcesado]:
    paginas_ocr = extraer_texto_ocr_hibrido_paginas(file_bytes)
    if not paginas_ocr:  # fallback si no pudimos rasterizar el PDF
        return []

    texto_total = " ".join(paginas_ocr)
    tipo = detectar_tipo_documento(texto_total)
    # Debug opcional: dejar descomentado solo en desarrollo
    # print("📄 Tipo detectado:", tipo)

    extractor_map: dict[str, Callable[[str], List[DocumentoProcesado]]] = {
        "factura": extraer_factura,
        "recibo": extraer_recibo,
        "transferencia": extraer_transferencias,
        "bancario": extraer_transferencias,
        "desconocido": extraer_por_tipos_combinados,
    }

    extractor = extractor_map.get(tipo, extraer_por_tipos_combinados)
    resultados: List[DocumentoProcesado] = []
    for pagina_texto in paginas_ocr:
        try:
            documentos = extractor(pagina_texto)
            resultados.extend(documentos)
        except Exception:
            continue

    # Normalización de tipo
    return [_normalizar_tipo_por_importe(d) for d in resultados]
