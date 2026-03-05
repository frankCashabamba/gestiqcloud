"""Parser para movimientos bancarios en XLSX/XLS.

Heurísticas de cabeceras comunes en extractos (fecha, valor, importe, concepto,
iban, referencia, moneda). Devuelve documentos canónicos doc_type=bank_tx.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

import openpyxl

from app.services.excel_analyzer import detect_header_row, extract_headers


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
        header_row, headers, row_iter = _iter_excel_rows(file_path, sheet_name=sheet_name)
        col_map = _map_columns(tuple(headers))
        for row_idx, row in row_iter:
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
        elif any(k in lower for k in ["amount", "importe", "monto"]):
            col_map["amount"] = idx
        elif "valor" in lower:
            col_map.setdefault("amount", idx)
        elif any(k in lower for k in ["direction", "tipo", "debito", "credito", "signo"]):
            col_map.setdefault("direction", idx)
        elif any(
            k in lower for k in ["concepto", "descripcion", "description", "detalle", "narrativa"]
        ):
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
            # Excel serial date
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
    transactions: list[dict[str, Any]],
    rows_processed: int,
    errors: list[str],
    file_path: str | None = None,
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
        "fecha",
        "valor",
        "importe",
        "monto",
        "concepto",
        "descripcion",
        "iban",
        "saldo",
        "cuenta",
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
