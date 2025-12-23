"""Parser de facturas en Excel (XLSX/XLS).

Lee cabeceras comunes (numero, fecha, proveedor/cliente, subtotal/iva/total, moneda)
y devuelve documentos canónicos doc_type=invoice.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import openpyxl


def parse_xlsx_invoices(file_path: str, sheet_name: str | None = None) -> dict[str, Any]:
    """Parsea facturas en Excel."""
    invoices: list[dict[str, Any]] = []
    errors: list[str] = []
    rows_processed = 0

    try:
        wb = openpyxl.load_workbook(file_path, data_only=True, read_only=True)
        ws = wb[sheet_name] if sheet_name else wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return _result(invoices, rows_processed, errors, file_path)

        header = rows[0]
        col_map = _map_columns(header)

        for row_idx, row in enumerate(rows[1:], start=2):
            rows_processed += 1
            if not row or all(cell is None or str(cell).strip() == "" for cell in row):
                continue
            try:
                inv = _parse_row(row, row_idx, col_map)
                if inv:
                    invoices.append(inv)
            except Exception as e:  # pragma: no cover - defensivo
                errors.append(f"row {row_idx}: {e}")
    except Exception as e:
        errors.append(f"read_error: {e}")

    return _result(invoices, rows_processed, errors, file_path)


def _map_columns(header: tuple) -> dict[str, int]:
    col_map: dict[str, int] = {}
    for idx, name in enumerate(header):
        if not name:
            continue
        lower = str(name).strip().lower()
        if any(k in lower for k in ["numero", "factura", "invoice_number", "número"]):
            col_map.setdefault("invoice_number", idx)
        elif any(k in lower for k in ["fecha", "issue_date", "invoice_date", "emision"]):
            col_map.setdefault("issue_date", idx)
        elif any(k in lower for k in ["vencimiento", "due_date"]):
            col_map.setdefault("due_date", idx)
        elif any(k in lower for k in ["proveedor", "vendor", "supplier"]):
            col_map.setdefault("vendor", idx)
        elif any(k in lower for k in ["cliente", "buyer", "customer"]):
            col_map.setdefault("buyer", idx)
        elif any(k in lower for k in ["ruc", "tax_id", "rfc"]):
            # Se asigna tanto para vendor como buyer si no existen
            col_map.setdefault("tax_id", idx)
        elif any(k in lower for k in ["subtotal", "neto"]):
            col_map.setdefault("subtotal", idx)
        elif any(k in lower for k in ["iva", "tax", "impuesto"]):
            col_map.setdefault("tax", idx)
        elif any(k in lower for k in ["total", "importe_total", "amount"]):
            col_map.setdefault("total", idx)
        elif any(k in lower for k in ["moneda", "currency"]):
            col_map.setdefault("currency", idx)
        elif any(k in lower for k in ["forma_pago", "payment_method", "metodo"]):
            col_map.setdefault("payment_method", idx)
        elif any(k in lower for k in ["referencia", "reference", "ref"]):
            col_map.setdefault("payment_reference", idx)
    return col_map


def _parse_row(row: tuple, row_idx: int, col_map: dict[str, int]) -> dict[str, Any] | None:
    def pick(key: str):
        i = col_map.get(key)
        return row[i] if i is not None and i < len(row) else None

    invoice_number = pick("invoice_number") or f"XLSX-INV-{row_idx}"
    total = _to_float(pick("total"))
    if total is None:
        return None

    vendor_name = pick("vendor")
    buyer_name = pick("buyer")
    tax_id_val = pick("tax_id")

    inv = {
        "doc_type": "invoice",
        "invoice_number": str(invoice_number).strip(),
        "issue_date": _to_date(pick("issue_date")),
        "due_date": _to_date(pick("due_date")),
        "vendor": {
            "name": _clean_str(vendor_name),
            "tax_id": _clean_str(tax_id_val) if vendor_name else None,
        },
        "buyer": {
            "name": _clean_str(buyer_name),
            "tax_id": _clean_str(tax_id_val) if buyer_name else None,
        },
        "currency": (str(pick("currency")).strip() if pick("currency") else "USD"),
        "totals": {
            "subtotal": _to_float(pick("subtotal")),
            "tax": _to_float(pick("tax")),
            "total": total,
        },
        "payment": {
            "method": (_clean_str(pick("payment_method")) or "cash"),
            "reference": _clean_str(pick("payment_reference")),
        },
        "source": "xlsx",
        "confidence": 0.8,
        "_metadata": {"parser": "xlsx_invoices", "row_index": row_idx},
    }
    return _clean_dict(inv)


def _to_float(val) -> float | None:
    if val is None or val == "":
        return None
    try:
        return float(str(val).replace(",", "."))
    except (ValueError, TypeError):
        return None


def _to_date(val):
    if val is None or val == "":
        return None
    if isinstance(val, datetime):
        return val.date().isoformat()
    if isinstance(val, (int, float)):
        try:
            return datetime.fromordinal(datetime(1899, 12, 30).toordinal() + int(val)).date().isoformat()
        except Exception:
            return str(val)
    return str(val)


def _clean_str(val) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    return s or None


def _clean_dict(d: dict) -> dict:
    if not isinstance(d, dict):
        return d
    cleaned = {}
    for k, v in d.items():
        if isinstance(v, dict):
            nested = _clean_dict(v)
            if nested:
                cleaned[k] = nested
        elif v not in (None, "", []):
            cleaned[k] = v
    return cleaned


def _result(
    invoices: list[dict[str, Any]], rows_processed: int, errors: list[str], file_path: str | None = None
) -> dict[str, Any]:
    return {
        "invoices": invoices,
        "rows_processed": rows_processed,
        "rows_parsed": len(invoices),
        "errors": errors,
        "source_type": "xlsx",
        "parser": "xlsx_invoices",
        "metadata": {"file": Path(file_path).name if file_path else None},
    }
