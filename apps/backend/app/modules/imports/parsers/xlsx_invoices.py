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
        # Columnas mapeadas a campos canónicos (para detectar las NO mapeadas)
        mapped_indices = set(col_map.values())
        for row_idx, row in row_iter:
            rows_processed += 1
            if not row or all(cell is None or str(cell).strip() == "" for cell in row):
                continue
            try:
                inv = _parse_row(row, row_idx, col_map)
                if inv:
                    # Preservar columnas originales no mapeadas para que el frontend
                    # pueda mostrarlas (Vendedor, Sector, Tipo ID, etc.)
                    for col_idx, hdr in enumerate(headers):
                        if col_idx in mapped_indices:
                            continue
                        if col_idx < len(row):
                            val = row[col_idx]
                            if (
                                val is not None
                                and str(val).strip()
                                and str(val).strip().lower() != "nan"
                            ):
                                inv[hdr] = val
                    invoices.append(inv)
            except Exception as e:  # pragma: no cover - defensivo
                errors.append(f"row {row_idx}: {e}")

        has_line_items = any(
            k in col_map
            for k in ("line_description", "line_quantity", "line_unit_price", "line_code")
        )
        if has_line_items and len(invoices) > 1:
            invoices = _group_invoices_by_number(invoices)
    except Exception as e:
        errors.append(f"read_error: {e}")

    return _result(invoices, rows_processed, errors, file_path)


# Mapping from FIELD_ALIASES canonical keys to internal column map keys
_FIELD_TO_COLUMN: dict[str, str] = {
    "invoice_number": "invoice_number",
    "invoice_date": "issue_date",
    "client": "buyer",
    "provider": "vendor",
    "tax_id": "tax_id",
    "amount": "total",
    "tax": "tax",
    "currency": "currency",
    "product": "line_description",
    "quantity": "line_quantity",
    "price": "line_unit_price",
    "sku": "line_code",
}

# Additional direct header matches not covered by FIELD_ALIASES
_EXTRA_HEADER_MATCHES: dict[str, list[str]] = {
    "issue_date": [
        "fecha",
        "issue_date",
        "invoice_date",
        "emision",
        "fecha emision",
        "fecha emisión",
    ],
    "due_date": ["vencimiento", "due_date"],
    "subtotal": ["subtotal", "sub total", "base imponible"],
    "total": ["total", "importe_total", "amount", "total pagar", "total_pagar", "total a pagar"],
    "tax": ["iva", "tax", "impuesto", "igv"],
    "payment_method": ["forma_pago", "payment_method", "metodo", "forma de pago", "metodo_pago"],
    "payment_reference": ["referencia", "reference", "ref"],
    "total_payable": ["total pagar", "total_pagar", "neto", "total a pagar"],
    "retention": ["retencion", "retención", "retention"],
    "invoice_number": [
        "numero",
        "factura",
        "invoice_number",
        "número",
        "num. factura",
        "num factura",
        "nro",
        "folio",
        "comprobante",
    ],
    "vendor": ["proveedor", "vendor", "supplier", "emisor"],
    "buyer": ["cliente", "buyer", "customer", "destinatario", "comprador"],
    "tax_id": ["ruc", "tax_id", "rfc", "nif", "cif", "nit", "numero_identificacion"],
    "currency": ["moneda", "currency", "divisa"],
    "line_description": [
        "producto",
        "product",
        "articulo",
        "item",
        "descripcion",
        "description",
        "detalle",
        "concepto",
    ],
    "line_quantity": ["cantidad", "quantity", "qty", "unidades"],
    "line_unit_price": [
        "precio unitario",
        "precio",
        "unit_price",
        "precio_unitario",
        "p.u.",
        "p.v.p",
        "precio venta",
    ],
    "line_code": [
        "cod. producto",
        "codigo",
        "code",
        "sku",
        "barcode",
        "codigo_producto",
        "product_code",
    ],
}


def _map_columns(header: tuple) -> dict[str, int]:
    """Map Excel column headers to canonical field names using config aliases."""
    try:
        from app.modules.imports.config.aliases import FIELD_ALIASES

        db_aliases = FIELD_ALIASES.get("es", {})
    except Exception:
        db_aliases = {}

    # Build a combined lookup: field_key -> [aliases...]
    lookup: dict[str, list[str]] = {}
    for key, aliases in _EXTRA_HEADER_MATCHES.items():
        lookup[key] = [a.lower() for a in aliases]

    # Merge FIELD_ALIASES via _FIELD_TO_COLUMN mapping
    for alias_key, col_key in _FIELD_TO_COLUMN.items():
        if alias_key in db_aliases:
            existing = lookup.get(col_key, [])
            for alias in db_aliases[alias_key]:
                a_lower = alias.lower()
                if a_lower not in existing:
                    existing.append(a_lower)
            lookup[col_key] = existing

    col_map: dict[str, int] = {}
    for idx, name in enumerate(header):
        if not name:
            continue
        lower = str(name).strip().lower()
        # Find best match: prefer longer alias matches
        best_field = None
        best_len = 0
        for field, aliases in lookup.items():
            for alias in aliases:
                if alias in lower and len(alias) > best_len:
                    best_field = field
                    best_len = len(alias)
        if best_field:
            col_map.setdefault(best_field, idx)
    return col_map


_JUNK_PATTERNS = re.compile(r"(p[aá]gina|pagina|page|listado|reporte)", re.IGNORECASE)


def _parse_row(row: tuple, row_idx: int, col_map: dict[str, int]) -> dict[str, Any] | None:
    def pick(key: str):
        i = col_map.get(key)
        return row[i] if i is not None and i < len(row) else None

    raw_inv_num = pick("invoice_number")
    if raw_inv_num is not None:
        inv_str = str(raw_inv_num).strip()
        if _JUNK_PATTERNS.search(inv_str):
            return None
        if len(inv_str) < 3 and not re.search(r"\d", inv_str):
            return None

    invoice_number = raw_inv_num or f"XLSX-INV-{row_idx}"
    total = _to_float(pick("total"))
    if total is None:
        return None

    vendor_name = pick("vendor")
    buyer_name = pick("buyer")
    tax_id_val = pick("tax_id")

    inv: dict[str, Any] = {
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

    line_desc = _clean_str(pick("line_description"))
    line_qty = _to_float(pick("line_quantity"))
    line_up = _to_float(pick("line_unit_price"))
    line_code = _clean_str(pick("line_code"))
    if line_desc or line_qty is not None or line_up is not None or line_code:
        inv["_line"] = _clean_dict(
            {
                "description": line_desc,
                "quantity": line_qty,
                "unit_price": line_up,
                "code": line_code,
                "total": total,
            }
        )

    total_payable = _to_float(pick("total_payable"))
    if total_payable is not None:
        inv["_total_payable"] = total_payable

    retention = _to_float(pick("retention"))
    if retention is not None:
        inv["_retention"] = retention

    return _clean_dict(inv)


def _group_invoices_by_number(invoices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from collections import OrderedDict

    groups: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for inv in invoices:
        key = inv.get("invoice_number", "")
        groups.setdefault(key, []).append(inv)

    result: list[dict[str, Any]] = []
    for inv_num, rows in groups.items():
        if len(rows) == 1:
            row = rows[0]
            line = row.pop("_line", None)
            row.pop("_total_payable", None)
            row.pop("_retention", None)
            if line:
                row["lines"] = [line]
            result.append(row)
            continue

        first = rows[0]
        merged = {
            k: v
            for k, v in first.items()
            if k not in ("totals", "_line", "_total_payable", "_retention", "_metadata")
        }

        lines: list[dict[str, Any]] = []
        sum_subtotal = 0.0
        sum_tax = 0.0
        sum_total = 0.0
        total_payable: float | None = None

        for row in rows:
            line = row.get("_line")
            if line:
                lines.append(line)

            totals = row.get("totals", {})
            sum_total += totals.get("total", 0.0) or 0.0
            sum_subtotal += totals.get("subtotal", 0.0) or 0.0
            sum_tax += totals.get("tax", 0.0) or 0.0

            tp = row.get("_total_payable")
            if tp is not None:
                total_payable = tp

        final_total = total_payable if total_payable is not None else sum_total
        merged["totals"] = _clean_dict(
            {
                "subtotal": sum_subtotal or None,
                "tax": sum_tax or None,
                "total": final_total,
            }
        )

        retention = next(
            (r.get("_retention") for r in rows if r.get("_retention") is not None),
            None,
        )
        if retention is not None:
            merged["totals"]["retention"] = retention

        if lines:
            merged["lines"] = lines

        merged["_metadata"] = {
            "parser": "xlsx_invoices",
            "row_index": first.get("_metadata", {}).get("row_index"),
            "grouped_rows": len(rows),
        }

        result.append(merged)
    return result


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
