"""Servicio OCR y extracción de texto para el Importador."""
from __future__ import annotations
import csv
import io
import itertools
import logging
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any, Iterable, Tuple
import openpyxl
import datetime
from PIL import Image

logger = logging.getLogger("importador.ocr")

SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif", ".xlsx", ".xls", ".csv", ".xml", ".txt", ".zip"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"}

# UBL 2.1 namespaces
_UBL_NS = {
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
}


def detect_file_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    type_map = {
        ".pdf": "PDF", ".jpg": "JPG", ".jpeg": "JPG", ".png": "PNG", ".tiff": "IMG", ".bmp": "IMG", ".gif": "IMG",
        ".xlsx": "XLSX", ".xls": "XLS", ".csv": "CSV", ".xml": "XML", ".txt": "TXT", ".zip": "ZIP",
    }
    return type_map.get(ext, "UNKNOWN")


async def extract_text_from_file(file_bytes: bytes, filename: str) -> dict[str, Any]:
    """Extrae texto de cualquier archivo soportado.
    Returns: {"text": str, "pages": int, "structured_data": list[dict] | None, "format": str}
    """
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        return await _extract_pdf(file_bytes)
    elif ext in IMAGE_EXTENSIONS:
        return await _extract_image(file_bytes)
    elif ext in (".xlsx", ".xls"):
        try:
            return _extract_excel(file_bytes, ext=ext)
        except Exception as exc:
            logger.warning("Excel parse failed (%s): %s", ext, exc)
            return {"text": "", "pages": 1, "structured_data": None, "format": "EXCEL_ERROR", "error": str(exc)}
    elif ext == ".csv":
        return _extract_csv(file_bytes)
    elif ext == ".xml":
        try:
            return _extract_xml(file_bytes)
        except Exception as exc:
            logger.warning("XML parse failed: %s", exc)
            preview = file_bytes[:4000].decode("utf-8", errors="ignore")
            return {"text": preview, "pages": 1, "structured_data": None, "format": "XML_PARSE_ERROR", "error": str(exc)}
    elif ext == ".txt":
        return _extract_txt(file_bytes)
    elif ext == ".zip":
        return _extract_zip_summary(file_bytes, filename)
    else:
        raise ValueError(f"Formato no soportado: {ext}")


def iter_zip_entries(file_bytes: bytes, max_files: int = 20, max_size_bytes: int = 8 * 1024 * 1024) -> Iterable[Tuple[str, bytes]]:
    """Itera ficheros válidos dentro de un ZIP.

    - Ignora directorios y ficheros vacíos.
    - Limita número de entradas y tamaño por archivo para evitar OOM.
    - Solo devuelve extensiones soportadas.
    """
    with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
        count = 0
        for info in zf.infolist():
            if info.is_dir():
                continue
            if info.file_size <= 0 or info.file_size > max_size_bytes:
                logger.warning("Zip entry %s skipped (size %s bytes)", info.filename, info.file_size)
                continue
            ext = Path(info.filename).suffix.lower()
            if ext not in SUPPORTED_EXTENSIONS:
                logger.warning("Zip entry %s skipped (ext %s no soportada)", info.filename, ext)
                continue
            with zf.open(info) as fp:
                yield info.filename, fp.read()
                count += 1
                if count >= max_files:
                    logger.warning("Zip truncado a %s ficheros", max_files)
                    break


def _extract_zip_summary(file_bytes: bytes, zip_name: str) -> dict[str, Any]:
    """Devuelve un resumen de contenido de un ZIP (no reemplaza el fan-out por archivo).

    Se usa solo para mostrar preview rápida si se sube el ZIP como un único documento.
    El fan-out real lo maneja router/run antes de llamar a este extractor.
    """
    summaries = []
    for inner_name, inner_bytes in iter_zip_entries(file_bytes):
        summaries.append({"filename": inner_name, "size": len(inner_bytes)})
    text = "\n".join(f"{s['filename']} ({s['size']} bytes)" for s in summaries)
    return {"text": text, "pages": 1, "structured_data": summaries, "format": "ZIP"}


async def _extract_pdf(file_bytes: bytes) -> dict[str, Any]:
    """PDF: intenta texto embebido con PyMuPDF, si no hay, usa OCR."""
    try:
        import fitz
    except ImportError:
        raise RuntimeError("PyMuPDF (fitz) no disponible")

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text_parts = []
    total_chars = 0

    try:
        for page in doc:
            page_text = page.get_text()
            if page_text.strip():
                total_chars += len(page_text.strip())
                text_parts.append(page_text)

        pages = len(doc)
    finally:
        doc.close()

    # If embedded text is sufficient, use it
    if total_chars > 50:
        return {"text": "\n".join(text_parts), "pages": pages, "structured_data": None, "format": "PDF"}

    # Otherwise, convert pages to images and OCR
    # Strategy 1: Use PyMuPDF native rendering (no Poppler needed)
    doc2 = fitz.open(stream=file_bytes, filetype="pdf")
    try:
        ocr_texts = []
        for page in doc2:
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            ocr_texts.append(_ocr_image(img))
        combined = "\n\n".join(t for t in ocr_texts if t)
        if combined.strip():
            return {"text": combined, "pages": len(doc2), "structured_data": None, "format": "PDF_OCR"}
    except Exception as exc:
        logger.warning("PyMuPDF OCR fallback failed: %s", exc)
    finally:
        doc2.close()

    # Strategy 2: pdf2image (requires Poppler)
    try:
        from pdf2image import convert_from_bytes
        images = convert_from_bytes(file_bytes, dpi=300)
        ocr_texts = []
        for img in images:
            ocr_texts.append(_ocr_image(img))
        return {"text": "\n\n".join(ocr_texts), "pages": len(images), "structured_data": None, "format": "PDF_OCR"}
    except Exception as exc:
        logger.warning("pdf2image OCR fallback failed: %s", exc)
        return {"text": "\n".join(text_parts) if text_parts else "", "pages": pages, "structured_data": None, "format": "PDF"}


async def _extract_image(file_bytes: bytes) -> dict[str, Any]:
    """Image: OCR with Tesseract with preprocessing for better results."""
    from PIL import ImageEnhance, ImageFilter
    img = Image.open(io.BytesIO(file_bytes))

    # Resize if too small — Tesseract works best at ~300 DPI equivalent
    min_width = 1800
    if img.width < min_width:
        scale = min_width / img.width
        img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)

    # Convert to grayscale
    if img.mode != "L":
        img = img.convert("L")

    # Enhance contrast and sharpness before OCR (helps with WhatsApp compressed photos)
    img = ImageEnhance.Contrast(img).enhance(1.8)
    img = ImageEnhance.Sharpness(img).enhance(2.0)
    img = img.filter(ImageFilter.SHARPEN)

    text = _ocr_image(img)
    return {"text": text, "pages": 1, "structured_data": None, "format": "IMAGE_OCR"}


def _ocr_image(img: Image.Image) -> str:
    """Run Tesseract OCR on a PIL Image."""
    try:
        import pytesseract
        text = pytesseract.image_to_string(img, lang="spa+eng")
        return text.strip()
    except Exception as exc:
        logger.warning("Tesseract OCR failed: %s", exc)
        try:
            import easyocr
            reader = easyocr.Reader(["es", "en"], gpu=False)
            import numpy as np
            results = reader.readtext(np.array(img))
            return "\n".join([r[1] for r in results])
        except Exception as exc2:
            logger.error("All OCR engines failed: %s", exc2)
            return ""


def _normalize_header(h: Any, idx: int) -> str:
    return str(h or f"col_{idx}").strip().lower().replace(" ", "_")


def _detect_col_type(values: list[Any]) -> str:
    num = sum(isinstance(v, (int, float)) for v in values if v is not None)
    dates = sum(isinstance(v, (datetime.date, datetime.datetime)) for v in values if v is not None)
    strings = sum(isinstance(v, str) for v in values if v is not None)
    counts = {"number": num, "date": dates, "string": strings}
    return max(counts, key=counts.get)


def _iter_xls_rows(file_bytes: bytes):
    try:
        import xlrd
    except ImportError:
        raise RuntimeError("Falta dependencia xlrd para archivos .xls (pip install xlrd)")
    book = xlrd.open_workbook(file_contents=file_bytes)
    for sheet in book.sheets():
        yield sheet.name, (sheet.nrows, sheet.ncols), (
            [sheet.cell_value(r, c) for c in range(sheet.ncols)] for r in range(sheet.nrows)
        )


def _iter_xlsx_rows(file_bytes: bytes):
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    try:
        for ws in wb.worksheets:
            yield ws.title, (ws.max_row or 0, ws.max_column or 0), ws.iter_rows(values_only=True)
    finally:
        wb.close()


def _score_header_row(row: tuple | list) -> float:
    """Score a row as a potential header row. Higher = more likely to be a header.

    Good headers: many non-empty strings, no numbers, short label-like text (ALL-CAPS / Title).
    Bad headers: lots of numbers, single text value, very long strings (prose, not labels).
    Minimum 2 unique text values required — single-value rows (titles, totals) are excluded.
    """
    if not row:
        return 0.0
    values = [v for v in row if v is not None]
    if not values:
        return 0.0
    text_vals = [str(v).strip() for v in values if isinstance(v, str) and str(v).strip()]
    numeric_count = sum(1 for v in values if isinstance(v, (int, float)) and not isinstance(v, bool))
    if not text_vals:
        return 0.0
    unique_text = len(set(t.upper() for t in text_vals))
    # Require at least 2 unique text values — single-value rows (titles/totals) cannot be headers
    if unique_text < 2:
        return 0.0
    # Prefer all-caps or title-case labels (typical for column headers)
    caps_count = sum(1 for t in text_vals if t.isupper() or t.istitle())
    # Prefer short labels (column names are usually < 40 chars); long prose is likely data
    avg_len = sum(len(t) for t in text_vals) / len(text_vals)
    length_bonus = 1.0 if avg_len <= 25 else 0.0
    # Prefer rows where most cells are non-null (dense rows = likely headers)
    fill_ratio = len(values) / max(len(row), 1)
    # Penalize rows with numbers (data rows have lots of numbers; header rows rarely do)
    score = (unique_text * 2.0) + (caps_count * 0.5) + (length_bonus * 1.0) + (fill_ratio * 1.5) - (numeric_count * 3.0)
    return score


def _find_header_row(initial_rows: list[tuple | list]) -> tuple[int, list]:
    """Scan rows and return (best_index, best_row) most likely to be the header.

    Prefers rows closer to the start when scores are equal, so a title in row 0
    does not displace a proper header in row 1.
    """
    if not initial_rows:
        return 0, []
    scores = [_score_header_row(r) for r in initial_rows]
    best_score = max(scores)
    if best_score <= 0.0:
        # No valid header found — return first non-empty row
        for i, r in enumerate(initial_rows):
            if any(v is not None for v in r):
                return i, list(r)
        return 0, list(initial_rows[0])
    # Among rows with the best score, prefer the earliest (smallest index)
    best_idx = next(i for i, s in enumerate(scores) if s == best_score)
    return best_idx, list(initial_rows[best_idx])


def _extract_kv_pairs(rows_before_header: list[tuple | list]) -> dict[str, Any]:
    """Extrae pares clave/valor en la sección superior de la hoja (antes del header).

    Heurística simple: toma cada celda de texto como posible clave y asigna
    el primer valor no vacío hacia la derecha en la misma fila.
    """
    kv: dict[str, Any] = {}
    for row in rows_before_header:
        if not row:
            continue
        # Requiere al menos dos valores no vacíos para considerar la fila útil
        non_null = [v for v in row if v not in (None, "")]
        if len(non_null) < 2:
            continue
        idx = 0
        row_list = list(row)
        while idx < len(row_list):
            label = row_list[idx]
            if not (isinstance(label, str) and label.strip() and len(label.strip()) <= 60):
                idx += 1
                continue
            label_clean = label.strip()
            value = None
            next_idx = idx + 1
            while next_idx < len(row_list):
                v = row_list[next_idx]
                if v is None or (isinstance(v, str) and not v.strip()):
                    next_idx += 1
                    continue
                value = v
                break
            if value is not None:
                key_norm = _normalize_header(label_clean, idx)
                if key_norm not in kv:
                    kv[key_norm] = value
                idx = next_idx + 1
            else:
                idx += 1
    return kv


def _extract_excel(file_bytes: bytes, ext: str = ".xlsx") -> dict[str, Any]:
    """Stream Excel safely, build fingerprint and a small preview (no OOM)."""
    MAX_HEADER_SCAN = 25          # rows scanned to find the real header row
    MAX_PREVIEW_ROWS_PER_SHEET = 120
    MAX_SCAN_ROWS_PER_SHEET = MAX_PREVIEW_ROWS_PER_SHEET * 4
    MAX_TEXT_CHARS = 4000

    row_iters = _iter_xls_rows(file_bytes) if ext == ".xls" else _iter_xlsx_rows(file_bytes)

    all_preview_rows: list[dict[str, Any]] = []
    text_lines: list[str] = []
    sheet_profiles: dict[str, Any] = {}
    sheet_metadata: dict[str, dict[str, Any]] = {}
    sheet_used = None
    best_score = -1

    for sheet_name, (nrows, ncols), rows_iter in row_iters:
        rows_iter = iter(rows_iter)

        # Scan first N rows to find the most likely header row
        initial_rows: list[tuple | list] = []
        for _ in range(MAX_HEADER_SCAN):
            try:
                initial_rows.append(next(rows_iter))
            except StopIteration:
                break

        if not initial_rows:
            continue

        header_idx, first_row = _find_header_row(initial_rows)
        # Capturar metadatos antes del header (títulos, pares clave/valor)
        kv_pairs = _extract_kv_pairs(initial_rows[:header_idx])

        # Rows AFTER the header row (from the scanned batch) become the first data rows
        data_prefix = [initial_rows[i] for i in range(header_idx + 1, len(initial_rows))]
        rows_iter = itertools.chain(data_prefix, rows_iter)

        # Build headers from the detected header row, using the max column count
        # seen in ALL scanned rows (so data columns not represented in headers get col_N names)
        max_cols = max((len(r) for r in initial_rows), default=len(first_row))
        if len(first_row) < max_cols:
            first_row = list(first_row) + [None] * (max_cols - len(first_row))

        headers = [_normalize_header(h, i) for i, h in enumerate(first_row)]
        header_display = [str(h or f"col_{i}") for i, h in enumerate(first_row)]
        sample_values_by_col: dict[str, list[Any]] = {h: [] for h in headers}

        preview_rows_sheet: list[dict[str, Any]] = []
        total_rows_counted = 0

        for row in rows_iter:
            total_rows_counted += 1
            if all(v is None for v in row):
                continue
            # Si la fila tiene más columnas que el header, crear col_N para las extras
            row_list = list(row)
            if len(row_list) > len(headers):
                for extra_i in range(len(headers), len(row_list)):
                    headers.append(f"col_{extra_i}")
                    header_display.append(f"col_{extra_i}")
                    sample_values_by_col[f"col_{extra_i}"] = []
            row_dict = {headers[j]: row_list[j] for j in range(min(len(headers), len(row_list)))}
            # Normaliza fechas numéricas en .xls si parecen fechas Excel
            if ext == ".xls":
                for k, v in list(row_dict.items()):
                    if isinstance(v, (int, float)):
                        try:
                            import xlrd
                            dt = xlrd.xldate_as_datetime(v, 0)
                            row_dict[k] = dt
                        except Exception:
                            pass
            row_dict["_sheet"] = sheet_name

            if len(preview_rows_sheet) < MAX_PREVIEW_ROWS_PER_SHEET:
                preview_rows_sheet.append(row_dict)
                for h in headers:
                    sample_values_by_col[h].append(row_dict.get(h))

            if total_rows_counted >= MAX_SCAN_ROWS_PER_SHEET:
                break

        text_lines.append(f"[{sheet_name}] " + "\t".join(header_display))
        for row in preview_rows_sheet[:30]:
            text_lines.append(f"[{sheet_name}] " + "\t".join(str(row.get(h, "") or "") for h in headers))

        col_profiles = {}
        for h, vals in sample_values_by_col.items():
            if not vals:
                continue
            col_profiles[h] = {"type": _detect_col_type(vals)}

        score = len(preview_rows_sheet)
        headers_lower = [h.lower() for h in headers]
        if any("fecha" in h or "date" in h for h in headers_lower):
            score += 50
        if any("monto" in h or "total" in h or "importe" in h for h in headers_lower):
            score += 20
        if score > best_score:
            best_score = score
            sheet_used = sheet_name

        all_preview_rows.extend(preview_rows_sheet)
        sheet_profiles[sheet_name] = {
            "rows_previewed": len(preview_rows_sheet),
            "rows_counted": total_rows_counted,
            "headers": header_display,
            "headers_norm": headers,
            "column_profiles": col_profiles,
            "kv_pairs": kv_pairs,
        }
        sheet_metadata[sheet_name] = kv_pairs

    text = "\n".join(text_lines)
    if len(text) > MAX_TEXT_CHARS:
        text = text[:MAX_TEXT_CHARS]

    return {
        "text": text,
        "pages": 1,
        "structured_data": all_preview_rows,
        "format": "EXCEL",
        "sheet_used": sheet_used,
        "sheet_profiles": sheet_profiles,
        "sheet_metadata": sheet_metadata,
    }


def _extract_csv(file_bytes: bytes) -> dict[str, Any]:
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            text_content = file_bytes.decode(enc)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    else:
        text_content = file_bytes.decode("utf-8", errors="replace")

    # Auto-detect delimiter
    sniffer = csv.Sniffer()
    try:
        dialect = sniffer.sniff(text_content[:2048])
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ","

    reader = csv.DictReader(io.StringIO(text_content), delimiter=delimiter)
    data = [row for row in reader if any(v and v.strip() for v in row.values())]
    return {"text": text_content[:10000], "pages": 1, "structured_data": data, "format": "CSV"}


def _extract_xml(file_bytes: bytes) -> dict[str, Any]:
    """XML UBL 2.1 extraction with graceful fallback on malformed XML."""
    try:
        root = ET.fromstring(file_bytes)
    except Exception as exc:
        # Malformed XML: degrade to text preview and mark parse error, but do NOT raise
        preview = file_bytes[:4000].decode("utf-8", errors="ignore")
        return {
            "text": preview,
            "pages": 1,
            "structured_data": None,
            "format": "XML_PARSE_ERROR",
            "error": str(exc),
        }
    tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag
    is_credit_note = tag.lower() in ("creditnote", "debitnote")

    ns = _UBL_NS

    def find_text(*paths):
        for p in paths:
            el = root.find(p, ns)
            if el is not None and el.text:
                return el.text.strip()
        return None

    header = {
        "documento": find_text("cbc:ID", ".//cbc:ID"),
        "fecha": find_text("cbc:IssueDate", ".//cbc:IssueDate"),
        "moneda": find_text("cbc:DocumentCurrencyCode"),
        "tipo_documento": "NOTA_CREDITO" if is_credit_note else "FACTURA",
    }

    # Supplier
    supplier = root.find(".//cac:AccountingSupplierParty//cac:Party", ns)
    if supplier is not None:
        tax_scheme = supplier.find(".//cac:PartyTaxScheme", ns)
        if tax_scheme is not None:
            el = tax_scheme.find("cbc:CompanyID", ns)
            if el is not None and el.text:
                header["ruc"] = el.text.strip()
        name_el = supplier.find(".//cac:PartyName/cbc:Name", ns)
        if name_el is not None and name_el.text:
            header["proveedor"] = name_el.text.strip()

    # Totals
    monetary = root.find(".//cac:LegalMonetaryTotal", ns)
    if monetary is not None:
        st = monetary.find("cbc:TaxExclusiveAmount", ns)
        if st is not None and st.text:
            header["subtotal"] = st.text.strip()
        pa = monetary.find("cbc:PayableAmount", ns)
        if pa is not None and pa.text:
            header["monto"] = pa.text.strip()

    tax_total = root.find(".//cac:TaxTotal", ns)
    if tax_total is not None:
        ta = tax_total.find("cbc:TaxAmount", ns)
        if ta is not None and ta.text:
            header["igv"] = ta.text.strip()

    # Credit note: negate amounts
    if is_credit_note:
        for field in ("monto", "subtotal", "igv"):
            if header.get(field):
                try:
                    val = float(header[field])
                    if val > 0:
                        header[field] = str(-val)
                except (ValueError, TypeError):
                    pass

    full_text = ET.tostring(root, encoding="unicode", method="text")
    return {"text": full_text[:10000] if full_text else str(header), "pages": 1, "structured_data": [header], "format": "XML_UBL"}


def _extract_txt(file_bytes: bytes) -> dict[str, Any]:
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            text_content = file_bytes.decode(enc)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    else:
        text_content = file_bytes.decode("utf-8", errors="replace")

    return {"text": text_content, "pages": 1, "structured_data": None, "format": "TXT"}
