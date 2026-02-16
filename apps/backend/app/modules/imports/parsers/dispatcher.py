"""Dispatcher que selecciona parser según extensión, content-type o cabeceras."""

from __future__ import annotations

from pathlib import Path

import openpyxl

from app.services.excel_analyzer import detect_header_row, extract_headers

from . import registry
from .generic_excel import parse_excel_generic

# Map ext/mime -> parser_id preferente
_EXT_PREFERENCES = {
    ".csv": {
        "bank": "csv_bank",
        "bank_transactions": "csv_bank",
        "products": "csv_products",
        "invoices": "csv_invoices",
        "expenses": "xlsx_expenses",  # CSV gasto no existe; cae a xlsx_expenses con pandas/openpyxl
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
        "generic": "pdf_ocr",
    },
}


def select_parser_for_file(
    file_path: str,
    *,
    content_type: str | None = None,
    hinted_doc_type: str | None = None,
    original_filename: str | None = None,
) -> tuple[str, str]:
    """Devuelve (parser_id, detected_doc_type) para un archivo.

    - Usa extensión/mime + hint de doc_type (batch.source_type)
    - Para XLSX/XLS inspecciona cabeceras y usa heurísticas
    - Fallback: generic_excel
    """
    ext = Path(original_filename or file_path).suffix.lower()
    hint = (hinted_doc_type or "").lower()

    # Mapeo directo por extensión + hint
    if ext in _EXT_PREFERENCES and hint:
        parser_id = _EXT_PREFERENCES[ext].get(hint)
        if parser_id and registry.get_parser(parser_id):
            return parser_id, registry.get_parser(parser_id)["doc_type"]

    # XLSX/XLS: inspeccionar cabeceras
    if ext in (".xlsx", ".xls", ".xlsm", ".xlsb"):
        try:
            detected_parser, detected_doc = _detect_excel_parser(
                file_path, hinted_doc_type=hint or None
            )
            return detected_parser, detected_doc
        except Exception:
            pass

    # PDF: usar pdf_ocr directamente (detecta tipo internamente)
    if ext == ".pdf" and registry.get_parser("pdf_ocr"):
        return "pdf_ocr", "generic"

    # Images: use image_ocr directly
    if ext in (
        ".png",
        ".jpg",
        ".jpeg",
        ".tiff",
        ".bmp",
        ".gif",
        ".heic",
        ".heif",
    ) and registry.get_parser("image_ocr"):
        return "image_ocr", "generic"

    # Fallback por extensión sin hint
    if ext in _EXT_PREFERENCES:
        for parser_id in _EXT_PREFERENCES[ext].values():
            if registry.get_parser(parser_id):
                return parser_id, registry.get_parser(parser_id)["doc_type"]

    # Fallback por mime (pdf → pdf_ocr)
    if content_type and "pdf" in content_type and registry.get_parser("pdf_ocr"):
        return "pdf_ocr", registry.get_parser("pdf_ocr")["doc_type"]

    # Último recurso: genérico
    return "generic_excel", "generic"


def _detect_excel_parser(file_path: str, *, hinted_doc_type: str | None = None) -> tuple[str, str]:
    """Detectar parser para Excel por cabeceras/keywords.

    Nota: el parser `xlsx_recipes` es un formato muy específico (PAN KUSI). Para evitar
    falsos positivos cuando el caller ya sabe el tipo esperado (p.ej. `products`),
    solo lo consideramos si:
    - no hay hint, o
    - el hint es `recipes`.
    """
    wb = openpyxl.load_workbook(file_path, data_only=True, read_only=True)
    try:
        ws = wb.active
        header_row = detect_header_row(ws)
        headers = extract_headers(ws, header_row)
        headers_str = " ".join([str(h or "").lower() for h in headers])

        # Always scan a few top rows as many "template" Excels (like costing sheets)
        # have a title row as header and the real signals appear below.
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

    # Heurísticas de palabras clave
    bank_kw = ("iban", "saldo", "cuenta", "concepto", "valor", "importe", "transaction", "bank")
    invoice_kw = ("factura", "invoice", "iva", "proveedor", "cliente", "ruc", "tax")
    expenses_kw = ("gasto", "expense", "receipt", "recibo", "categoria")
    product_kw = ("producto", "sku", "precio", "stock", "categoria")
    recipe_kw = (
        "ingredientes",
        "costo total ingredientes",
        "formato de costeo",
        "receta",
        "porciones",
        "temperatura de servicio",
    )

    hint = (hinted_doc_type or "").strip().lower()

    # Costing template: for products flow, parse it as products (price list); for recipes flow, parse as recipes.
    if any(k in haystack for k in recipe_kw):
        # If explicitly hinted as recipes, keep recipes.
        if hint in ("recipes", "recipe") and registry.get_parser("xlsx_recipes"):
            return "xlsx_recipes", registry.get_parser("xlsx_recipes")["doc_type"]
        # Otherwise default to "products" view (one sheet -> one product with suggested price).
        if registry.get_parser("xlsx_costing_products"):
            return "xlsx_costing_products", registry.get_parser("xlsx_costing_products")["doc_type"]
        if registry.get_parser("xlsx_recipes"):
            return "xlsx_recipes", registry.get_parser("xlsx_recipes")["doc_type"]
    if any(k in haystack for k in bank_kw) and registry.get_parser("xlsx_bank"):
        return "xlsx_bank", registry.get_parser("xlsx_bank")["doc_type"]
    if any(k in haystack for k in invoice_kw) and registry.get_parser("xlsx_invoices"):
        return "xlsx_invoices", registry.get_parser("xlsx_invoices")["doc_type"]
    if any(k in haystack for k in expenses_kw) and registry.get_parser("xlsx_expenses"):
        return "xlsx_expenses", registry.get_parser("xlsx_expenses")["doc_type"]
    if any(k in haystack for k in product_kw) and registry.get_parser("products_excel"):
        return "products_excel", registry.get_parser("products_excel")["doc_type"]

    # Si no se detecta, usar genérico pero con doc_type detectado por parser
    gen = parse_excel_generic(file_path)
    return "generic_excel", gen.get("detected_type", "generic")
