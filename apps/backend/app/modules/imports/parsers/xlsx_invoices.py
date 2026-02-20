"""Parser de facturas en Excel (XLSX/XLS).

Lee cabeceras comunes (numero, fecha, proveedor/cliente, subtotal/iva/total, moneda)
y devuelve documentos canónicos doc_type=invoice.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

import openpyxl

from app.services.excel_analyzer import detect_header_row, extract_headers


def parse_xlsx_invoices(file_path: str, sheet_name: str | None = None) -> dict[str, Any]:
    """Parsea facturas en Excel."""
    invoices: list[dict[str, Any]] = []
    errors: list[str] = []
    rows_processed = 0

    try:
        header_row, headers, row_iter = _iter_excel_rows(file_path, sheet_name=sheet_name)
        col_map = _map_columns(tuple(headers))
        for row_idx, row in row_iter:
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
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if not s:
        return None
    s = re.sub(r"[^0-9,.\-]", "", s)
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _to_date(val):
    if val is None or val == "":
        return None
    if isinstance(val, datetime):
        return val.date().isoformat()
    if isinstance(val, (int, float)):
        try:
            return (
                datetime.fromordinal(datetime(1899, 12, 30).toordinal() + int(val))
                .date()
                .isoformat()
            )
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
    invoices: list[dict[str, Any]],
    rows_processed: int,
    errors: list[str],
    file_path: str | None = None,
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


def _iter_excel_rows(
    file_path: str,
    *,
    sheet_name: str | None = None,
) -> tuple[int, list[str], list[tuple[int, tuple[Any, ...]]]]:
    """Read headers and rows using openpyxl first, then pandas/xlrd for legacy XLS."""
    try:
        wb = openpyxl.load_workbook(file_path, data_only=True, read_only=True)
        try:
            ws = wb[sheet_name] if sheet_name else wb.active
            header_row = detect_header_row(ws)
            headers = extract_headers(ws, header_row)
            rows = list(
                enumerate(
                    ws.iter_rows(min_row=header_row + 1, values_only=True),
                    start=header_row + 1,
                )
            )
            return header_row, list(headers), [(idx, tuple(row)) for idx, row in rows]
        finally:
            try:
                wb.close()
            except Exception:
                pass
    except Exception:
        return _iter_excel_rows_pandas(file_path, sheet_name=sheet_name)


def _iter_excel_rows_pandas(
    file_path: str,
    *,
    sheet_name: str | None = None,
) -> tuple[int, list[str], list[tuple[int, tuple[Any, ...]]]]:
    try:
        import pandas as pd
    except Exception as e:  # pragma: no cover - environment dependent
        raise RuntimeError(f"pandas_not_available_for_xls_fallback: {e}") from e

    engine = "xlrd" if file_path.lower().endswith(".xls") else None
    try:
        df = pd.read_excel(file_path, engine=engine, header=None, sheet_name=sheet_name or 0)
    except Exception as e:
        if file_path.lower().endswith(".xls"):
            raise RuntimeError(f"xls_requires_xlrd_or_conversion: {e}") from e
        raise
    df = df.fillna("")
    if df.empty:
        return 1, [], []

    header_row_idx = _detect_header_row_in_df(df)
    headers: list[str] = []
    for i, value in enumerate(df.iloc[header_row_idx].tolist()):
        header = str(value).strip()
        if not header or header.lower() == "nan" or header.lower().startswith("unnamed"):
            header = f"col_{i + 1}"
        headers.append(header)

    rows: list[tuple[int, tuple[Any, ...]]] = []
    for row_idx in range(header_row_idx + 1, len(df.index)):
        row_values = tuple(df.iloc[row_idx].tolist())
        rows.append((row_idx + 1, row_values))

    return header_row_idx + 1, headers, rows


def _detect_header_row_in_df(df) -> int:
    keywords = [
        "factura",
        "invoice",
        "numero",
        "fecha",
        "proveedor",
        "cliente",
        "subtotal",
        "iva",
        "total",
    ]
    max_scan = min(len(df.index), 40)
    best_idx = 0
    best_score = -(10**9)
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
    return best_idx
