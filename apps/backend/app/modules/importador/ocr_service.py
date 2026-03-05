"""Servicio OCR y extracción de texto para el Importador."""
from __future__ import annotations
import csv
import io
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
import openpyxl
from PIL import Image

logger = logging.getLogger("importador.ocr")

SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif", ".xlsx", ".xls", ".csv", ".xml", ".txt"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"}

# UBL 2.1 namespaces
_UBL_NS = {
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
}


def detect_file_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    type_map = {".pdf": "PDF", ".jpg": "JPG", ".jpeg": "JPG", ".png": "PNG", ".tiff": "IMG", ".bmp": "IMG", ".gif": "IMG", ".xlsx": "XLSX", ".xls": "XLS", ".csv": "CSV", ".xml": "XML", ".txt": "TXT"}
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
        return _extract_excel(file_bytes)
    elif ext == ".csv":
        return _extract_csv(file_bytes)
    elif ext == ".xml":
        return _extract_xml(file_bytes)
    elif ext == ".txt":
        return _extract_txt(file_bytes)
    else:
        raise ValueError(f"Formato no soportado: {ext}")


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
    """Image: OCR with Tesseract."""
    img = Image.open(io.BytesIO(file_bytes))
    # Preprocessing: convert to grayscale for better OCR
    if img.mode != "L":
        img = img.convert("L")
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


def _extract_excel(file_bytes: bytes) -> dict[str, Any]:
    """Parse all Excel sheets instead of only the active one.

    Heuristics:
    - Collect rows from every worksheet (skipping empty rows).
    - Tag each row with `_sheet` so the UI/LLM knows the origin sheet.
    - Build a compact text sample per sheet (first 30 rows) to feed the LLM.
    - Pick the sheet with the highest signal (rows + presence of date/amount headers)
      as `sheet_used` for transparency.
    """
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)

    all_rows: list[dict[str, Any]] = []
    text_lines: list[str] = []
    sheet_scores: dict[str, int] = {}
    sheet_used = None
    best_score = -1

    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            continue

        headers = [str(h or f"col_{i}").strip() for i, h in enumerate(rows[0])]
        sheet_rows: list[dict[str, Any]] = []
        for row in rows[1:]:
            if all(v is None for v in row):
                continue
            row_dict = {headers[j]: row[j] for j in range(min(len(headers), len(row)))}
            row_dict["_sheet"] = ws.title
            sheet_rows.append(row_dict)

        if not sheet_rows:
            continue

        # Score the sheet: favor more rows and date/amount headers
        score = len(sheet_rows)
        headers_lower = [h.lower() for h in headers]
        if any("fecha" in h or "date" in h for h in headers_lower):
            score += 50
        if any("monto" in h or "total" in h or "importe" in h for h in headers_lower):
            score += 20
        if score > best_score:
            best_score = score
            sheet_used = ws.title

        all_rows.extend(sheet_rows)

        # Build a compact text sample for the LLM (limit to 30 rows per sheet)
        text_lines.append(f"[{ws.title}] " + "\t".join(headers))
        for row in sheet_rows[:30]:
            text_lines.append(
                f"[{ws.title}] "
                + "\t".join(str(row.get(h, "") or "") for h in headers)
            )

        sheet_scores[ws.title] = score

    wb.close()

    if not all_rows:
        return {"text": "", "pages": 1, "structured_data": [], "format": "EXCEL"}

    # Keep text short to avoid huge prompts (cap ~4000 chars)
    text = "\n".join(text_lines)
    if len(text) > 4000:
        text = text[:4000]

    return {
        "text": text,
        "pages": 1,
        "structured_data": all_rows,
        "format": "EXCEL",
        "sheet_used": sheet_used,
        "sheet_scores": sheet_scores,
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
    """XML UBL 2.1 extraction."""
    root = ET.fromstring(file_bytes)
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
