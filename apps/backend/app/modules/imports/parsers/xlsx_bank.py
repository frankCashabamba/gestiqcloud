"""Parser para movimientos bancarios en XLSX/XLS.

Heurísticas de cabeceras comunes en extractos (fecha, valor, importe, concepto,
iban, referencia, moneda). Devuelve documentos canónicos doc_type=bank_tx.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import openpyxl


def parse_xlsx_bank(file_path: str, sheet_name: str | None = None) -> dict[str, Any]:
    """Parsea un Excel de movimientos bancarios.

    Args:
        file_path: ruta al archivo .xlsx/.xls
        sheet_name: hoja a leer (opcional)

    Returns:
        Dict con `bank_transactions` y metadatos simples.
    """
    transactions: list[dict[str, Any]] = []
    errors: list[str] = []
    rows_processed = 0

    try:
        wb = openpyxl.load_workbook(file_path, data_only=True, read_only=True)
        if sheet_name:
            ws = wb[sheet_name]
        else:
            ws = wb.active

        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return _result(transactions, rows_processed, errors, file_path)

        header = rows[0]
        col_map = _map_columns(header)

        for row_idx, row in enumerate(rows[1:], start=2):
            rows_processed += 1
            if not row or all(cell is None or str(cell).strip() == "" for cell in row):
                continue
            try:
                tx = _parse_row(row, row_idx, col_map)
                if tx:
                    transactions.append(tx)
            except Exception as e:  # pragma: no cover - defensivo
                errors.append(f"row {row_idx}: {e}")

    except Exception as e:
        errors.append(f"read_error: {e}")

    return _result(transactions, rows_processed, errors, file_path)


def _map_columns(header: tuple) -> dict[str, int]:
    """Heurística de asignación de columnas por nombre."""
    col_map: dict[str, int] = {}
    for idx, name in enumerate(header):
        if not name:
            continue
        lower = str(name).strip().lower()

        if any(k in lower for k in ["transaction_date", "fecha", "fecha_transaccion", "fec.op"]):
            col_map.setdefault("transaction_date", idx)
        elif any(k in lower for k in ["value_date", "fecha_valor", "fecha valor"]):
            col_map.setdefault("value_date", idx)
        elif any(k in lower for k in ["amount", "importe", "monto", "valor"]):
            col_map.setdefault("amount", idx)
        elif any(k in lower for k in ["direction", "tipo", "debito", "credito", "signo"]):
            col_map.setdefault("direction", idx)
        elif any(k in lower for k in ["concepto", "descripcion", "description", "detalle", "narrativa"]):
            col_map.setdefault("narrative", idx)
        elif any(k in lower for k in ["counterparty", "contraparte", "beneficiario", "ordenante"]):
            col_map.setdefault("counterparty", idx)
        elif any(k in lower for k in ["reference", "referencia", "ref", "id", "transaction_id"]):
            col_map.setdefault("reference", idx)
        elif any(k in lower for k in ["iban", "cuenta", "account"]):
            col_map.setdefault("iban", idx)
        elif any(k in lower for k in ["currency", "moneda"]):
            col_map.setdefault("currency", idx)
    return col_map


def _parse_row(row: tuple, row_idx: int, col_map: dict[str, int]) -> dict[str, Any] | None:
    def pick(key: str):
        i = col_map.get(key)
        return row[i] if i is not None and i < len(row) else None

    amount_raw = pick("amount")
    amount = _to_float(amount_raw)
    if amount is None:
        return None

    direction_raw = pick("direction")
    direction = str(direction_raw).strip().lower() if direction_raw not in (None, "") else None
    if direction not in ("debit", "credit"):
        direction = "debit" if amount < 0 else "credit"

    tx = {
        "doc_type": "bank_tx",
        "issue_date": _to_date(pick("transaction_date")),
        "currency": (str(pick("currency")).strip() if pick("currency") else "USD"),
        "bank_tx": {
            "amount": abs(amount),
            "direction": direction,
            "value_date": _to_date(pick("value_date")) or _to_date(pick("transaction_date")),
            "narrative": _clean_str(pick("narrative")),
            "counterparty": _clean_str(pick("counterparty")),
            "external_ref": _clean_str(pick("reference")),
        },
        "payment": {"iban": _clean_str(pick("iban"))},
        "source": "xlsx",
        "confidence": 0.85,
        "_metadata": {"parser": "xlsx_bank", "row_index": row_idx},
    }
    return _clean_dict(tx)


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
            # Excel serial date
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
    """Remover claves nulas/vacías (profundo)."""
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
    transactions: list[dict[str, Any]], rows_processed: int, errors: list[str], file_path: str | None = None
) -> dict[str, Any]:
    return {
        "bank_transactions": transactions,
        "rows_processed": rows_processed,
        "rows_parsed": len(transactions),
        "errors": errors,
        "source_type": "xlsx",
        "parser": "xlsx_bank",
        "metadata": {"file": Path(file_path).name if file_path else None},
    }
