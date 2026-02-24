"""Dispatcher that selects parser by extension, content type, and lightweight heuristics."""

from __future__ import annotations

from pathlib import Path

import openpyxl

from app.services.excel_analyzer import detect_header_row, extract_headers

from . import registry
from .generic_excel import parse_excel_generic

# Preferred parser by extension + hinted document type
_EXT_PREFERENCES = {
    ".csv": {
        "bank": "csv_bank",
        "bank_transactions": "csv_bank",
        "products": "csv_products",
        "invoices": "csv_invoices",
        "expenses": "xlsx_expenses",
    },
    ".xml": {
        "invoices": "xml_invoice",
        "bank": "xml_camt053_bank",
        "bank_transactions": "xml_camt053_bank",
        "products": "xml_products",
    },
    ".pdf": {
        "invoices": "pdf_ocr",
        "expenses": "pdf_ocr",
        "receipts": "pdf_ocr",
        "ticket_pos": "pdf_ocr",
        "bank": "pdf_ocr",
        "generic": "pdf_qr",
    },
}

_PARSER_EXTENSION_ALLOWLIST: dict[str, tuple[str, ...]] = {
    "generic_excel": (".xlsx", ".xls", ".xlsm", ".xlsb"),
    "products_excel": (".xlsx", ".xls", ".xlsm", ".xlsb"),
    "xlsx_bank": (".xlsx", ".xls", ".xlsm", ".xlsb"),
    "xlsx_invoices": (".xlsx", ".xls", ".xlsm", ".xlsb"),
    "xlsx_expenses": (".xlsx", ".xls", ".xlsm", ".xlsb"),
    "xlsx_recipes": (".xlsx", ".xls", ".xlsm", ".xlsb"),
    "xlsx_costing_products": (".xlsx", ".xls", ".xlsm", ".xlsb"),
    "csv_bank": (".csv",),
    "csv_invoices": (".csv",),
    "csv_products": (".csv",),
    "xml_invoice": (".xml",),
    "xml_products": (".xml",),
    "xml_camt053_bank": (".xml",),
    "xml_facturae": (".xml",),
    "pdf_ocr": (".pdf",),
    "pdf_qr": (".pdf",),
    "image_ocr": (".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif", ".heic", ".heif"),
}


def is_parser_compatible_with_extension(parser_id: str | None, ext: str | None) -> bool:
    """Return True if parser is compatible with extension."""
    if not parser_id or not ext:
        return False
    normalized_ext = str(ext).lower()
    allowed = _PARSER_EXTENSION_ALLOWLIST.get(parser_id)
    if not allowed:
        return True
    return normalized_ext in allowed


def select_fallback_parser_for_extension(
    ext: str | None,
    *,
    content_type: str | None = None,
) -> tuple[str, str]:
    """Pick a safe fallback parser for file extension."""
    normalized_ext = str(ext or "").lower()

    if normalized_ext in (".xlsx", ".xls", ".xlsm", ".xlsb"):
        info = registry.get_parser("generic_excel")
        if info:
            return "generic_excel", info["doc_type"]
        return "generic_excel", "generic"

    if normalized_ext == ".csv":
        for parser_id in ("csv_invoices", "csv_products", "csv_bank"):
            info = registry.get_parser(parser_id)
            if info:
                return parser_id, info["doc_type"]

    if normalized_ext == ".xml":
        for parser_id in ("xml_invoice", "xml_products", "xml_camt053_bank", "xml_facturae"):
            info = registry.get_parser(parser_id)
            if info:
                return parser_id, info["doc_type"]

    if normalized_ext == ".pdf" or (content_type and "pdf" in content_type):
        for parser_id in ("pdf_ocr", "pdf_qr"):
            info = registry.get_parser(parser_id)
            if info:
                return parser_id, info["doc_type"]
        return "pdf_ocr", "generic"

    if normalized_ext in (
        ".png",
        ".jpg",
        ".jpeg",
        ".tiff",
        ".bmp",
        ".gif",
        ".heic",
        ".heif",
    ):
        info = registry.get_parser("image_ocr")
        if info:
            return "image_ocr", info["doc_type"]
        # Keep explicit image parser even if not registered so caller gets a clear parser_not_found
        # instead of trying to open an image as Excel.
        return "image_ocr", "generic"

    info = registry.get_parser("generic_excel")
    if info:
        return "generic_excel", info["doc_type"]
    return "generic_excel", "generic"


def select_parser_for_file(
    file_path: str,
    *,
    content_type: str | None = None,
    hinted_doc_type: str | None = None,
    original_filename: str | None = None,
) -> tuple[str, str]:
    """Return (parser_id, detected_doc_type) for a file."""
    ext = Path(original_filename or file_path).suffix.lower()
    hint = (hinted_doc_type or "").lower()

    if ext in _EXT_PREFERENCES and hint:
        parser_id = _EXT_PREFERENCES[ext].get(hint)
        if parser_id and registry.get_parser(parser_id):
            return parser_id, registry.get_parser(parser_id)["doc_type"]

    if ext in (".xlsx", ".xls", ".xlsm", ".xlsb"):
        try:
            detected_parser, detected_doc = _detect_excel_parser(
                file_path, hinted_doc_type=hint or None
            )
            return detected_parser, detected_doc
        except Exception:
            pass

    if ext == ".pdf":
        for parser_id in ("pdf_ocr", "pdf_qr"):
            if registry.get_parser(parser_id):
                return parser_id, registry.get_parser(parser_id)["doc_type"]

    if ext in (".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif", ".heic", ".heif"):
        if registry.get_parser("image_ocr"):
            return "image_ocr", registry.get_parser("image_ocr")["doc_type"]

    if ext in _EXT_PREFERENCES:
        for parser_id in _EXT_PREFERENCES[ext].values():
            if registry.get_parser(parser_id):
                return parser_id, registry.get_parser(parser_id)["doc_type"]

    if content_type and "pdf" in content_type:
        for parser_id in ("pdf_ocr", "pdf_qr"):
            if registry.get_parser(parser_id):
                return parser_id, registry.get_parser(parser_id)["doc_type"]

    return select_fallback_parser_for_extension(ext, content_type=content_type)


def _detect_excel_parser(file_path: str, *, hinted_doc_type: str | None = None) -> tuple[str, str]:
    """Detect parser for Excel files by scanning top rows/headers."""
    headers: list[str] = []
    haystack = ""

    is_legacy_xls = file_path.lower().endswith(".xls") and not file_path.lower().endswith(".xlsx")

    if not is_legacy_xls:
        wb = openpyxl.load_workbook(file_path, data_only=True, read_only=True)
        try:
            ws = wb.active
            header_row = detect_header_row(ws)
            headers = extract_headers(ws, header_row)
            headers_str = " ".join([str(h or "").lower() for h in headers])

            rows = list(ws.iter_rows(values_only=True, max_row=30))
            scan_str = " ".join(
                str(cell or "").lower() for row in rows for cell in row if cell not in (None, "")
            )
            haystack = f"{headers_str} {scan_str}".strip()
        finally:
            try:
                wb.close()
            except Exception:
                pass
    else:
        # Fallback for legacy .xls files using pandas + xlrd
        try:
            import pandas as pd  # type: ignore

            df = pd.read_excel(file_path, engine="xlrd", header=None, nrows=40)
            df = df.fillna("")
            if not df.empty:
                # Detect header row with keyword scoring
                keywords = [
                    "fecha", "factura", "cliente", "producto", "cantidad",
                    "precio", "subtotal", "iva", "total", "tipo", "codigo",
                    "descripcion", "vendedor", "stock", "categoria", "sku",
                    "nombre", "banco", "cuenta", "saldo",
                ]
                best_idx, best_score = 0, -1
                max_scan = min(len(df.index), 30)
                for idx in range(max_scan):
                    values = [str(v).strip() for v in df.iloc[idx].tolist()]
                    non_empty = [v for v in values if v and v.lower() != "nan"]
                    if len(non_empty) < 2:
                        continue
                    lowered = " ".join(v.lower() for v in non_empty)
                    kw_hits = sum(1 for kw in keywords if kw in lowered)
                    score = len(non_empty) + (kw_hits * 4)
                    if score > best_score:
                        best_score = score
                        best_idx = idx
                raw_headers = df.iloc[best_idx].tolist()
                headers = [str(h).strip() for h in raw_headers if str(h).strip() and str(h).lower() != "nan"]
                headers_str = " ".join(h.lower() for h in headers)
                scan_rows = []
                for row_idx in range(best_idx + 1, min(len(df.index), best_idx + 30)):
                    vals = df.iloc[row_idx].tolist()
                    scan_rows.extend(str(v).lower() for v in vals if v not in (None, "") and str(v).lower() != "nan")
                scan_str = " ".join(scan_rows)
                haystack = f"{headers_str} {scan_str}".strip()
        except Exception:
            pass

    if not haystack:
        raise ValueError("Could not read file headers")

    bank_kw = ("iban", "saldo", "cuenta", "concepto", "valor", "importe", "transaction", "bank")
    invoice_kw = ("factura", "invoice", "iva", "proveedor", "cliente", "ruc", "tax",
                  "vendedor", "num. factura", "num factura", "forma de pago", "retencion")
    expenses_kw = ("gasto", "expense", "receipt", "recibo")
    product_kw = ("sku", "stock", "existencias", "inventario", "barcode", "ean")
    recipe_kw = (
        "ingredientes",
        "costo total ingredientes",
        "formato de costeo",
        "receta",
        "porciones",
        "temperatura de servicio",
    )

    hint = (hinted_doc_type or "").strip().lower()
    lower_haystack = haystack.lower()

    def _kw_score(keywords: tuple[str, ...]) -> int:
        return sum(1 for k in keywords if k in lower_haystack)

    bank_score = _kw_score(bank_kw)
    invoice_score = _kw_score(invoice_kw)
    expenses_score = _kw_score(expenses_kw)
    product_score = _kw_score(product_kw)
    strong_bank_hits = _kw_score(("iban", "saldo", "cuenta", "importe", "monto", "debit", "credit"))

    if any(k in haystack for k in recipe_kw):
        # Default behavior for recipe-like workbooks should be recipes flow.
        # Only use costing-as-products when the caller explicitly hints products/inventory.
        if hint in ("products", "product", "productos", "inventario"):
            if registry.get_parser("xlsx_costing_products"):
                return "xlsx_costing_products", registry.get_parser("xlsx_costing_products")[
                    "doc_type"
                ]
        if registry.get_parser("xlsx_recipes"):
            return "xlsx_recipes", registry.get_parser("xlsx_recipes")["doc_type"]
        if registry.get_parser("xlsx_costing_products"):
            return "xlsx_costing_products", registry.get_parser("xlsx_costing_products")[
                "doc_type"
            ]
    if (
        registry.get_parser("xlsx_bank")
        and bank_score >= 2
        and strong_bank_hits >= 1
        and bank_score >= invoice_score
        and bank_score >= product_score
    ):
        return "xlsx_bank", registry.get_parser("xlsx_bank")["doc_type"]
    if (
        registry.get_parser("xlsx_invoices")
        and invoice_score >= 2
        and invoice_score >= bank_score
        and invoice_score >= product_score
    ):
        return "xlsx_invoices", registry.get_parser("xlsx_invoices")["doc_type"]
    if (
        registry.get_parser("xlsx_expenses")
        and expenses_score >= 2
        and expenses_score >= bank_score
        and expenses_score >= invoice_score
    ):
        return "xlsx_expenses", registry.get_parser("xlsx_expenses")["doc_type"]
    if (
        registry.get_parser("products_excel")
        and product_score >= 1
        and product_score >= bank_score
        and product_score >= invoice_score
    ):
        return "products_excel", registry.get_parser("products_excel")["doc_type"]

    gen = parse_excel_generic(file_path)
    return "generic_excel", gen.get("detected_type", "generic")
