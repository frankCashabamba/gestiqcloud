"""
Parser para transacciones bancarias en formato CSV.

Espera columnas: transaction_date, value_date, amount, direction (debit|credit),
narrative, counterparty, reference, iban, currency, etc.

Salida: lista de CanonicalDocument con doc_type='bank_tx'
"""

import csv
from typing import Any


def parse_csv_bank(file_path: str) -> dict[str, Any]:
    """
    Parse CSV file with bank transaction data.

    Args:
        file_path: Path to CSV file

    Returns:
        Dict with 'bank_transactions' list and metadata
    """
    transactions = []
    rows_processed = 0
    errors = []

    try:
        with open(file_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError("CSV file is empty or has no headers")

            for idx, row in enumerate(reader, start=1):
                rows_processed += 1

                # Normalizar nombres de columna
                normalized_row = {k.strip().lower(): v for k, v in row.items()}

                # Extraer amount y dirección
                amount_raw = _to_float(
                    normalized_row.get("amount")
                    or normalized_row.get("importe")
                    or normalized_row.get("monto")
                )

                # Si amount es negativo, es debit; sino, credit
                direction_raw = (
                    normalized_row.get("direction")
                    or normalized_row.get("tipo")
                    or ("debit" if amount_raw and amount_raw < 0 else "credit")
                )
                direction = direction_raw.lower().strip()
                if direction not in ("debit", "credit"):
                    direction = "credit"

                # Convertir a valor positivo si es negativo
                amount = abs(amount_raw) if amount_raw else 0.0

                # Construir documento canónico
                transaction = {
                    "doc_type": "bank_tx",
                    "issue_date": (
                        normalized_row.get("transaction_date")
                        or normalized_row.get("fecha_transaccion")
                        or normalized_row.get("fecha")
                    ),
                    "currency": (
                        normalized_row.get("currency") or normalized_row.get("moneda") or "USD"
                    ),
                    "bank_tx": {
                        "amount": amount,
                        "direction": direction,
                        "value_date": (
                            normalized_row.get("value_date")
                            or normalized_row.get("fecha_valor")
                            or normalized_row.get("transaction_date")
                            or normalized_row.get("fecha")
                        ),
                        "narrative": (
                            normalized_row.get("narrative")
                            or normalized_row.get("concepto")
                            or normalized_row.get("description")
                            or normalized_row.get("descripcion")
                        ),
                        "counterparty": (
                            normalized_row.get("counterparty")
                            or normalized_row.get("contraparte")
                            or normalized_row.get("account_holder")
                        ),
                        "external_ref": (
                            normalized_row.get("external_ref")
                            or normalized_row.get("reference")
                            or normalized_row.get("referencia")
                            or normalized_row.get("transaction_id")
                        ),
                    },
                    "payment": {
                        "iban": (
                            normalized_row.get("iban") or normalized_row.get("account_number")
                        ),
                    },
                    "source": "csv",
                    "confidence": 0.85,
                    "_metadata": {
                        "parser": "csv_bank",
                        "row_index": idx,
                    },
                }

                # Limpiar nulos
                transaction = _clean_dict(transaction)
                transactions.append(transaction)

    except Exception as e:
        errors.append(str(e))

    return {
        "bank_transactions": transactions,
        "rows_processed": rows_processed,
        "rows_parsed": len(transactions),
        "errors": errors,
        "source_type": "csv",
        "parser": "csv_bank",
    }


def _to_float(val) -> float | None:
    """Convertir a float o None."""
    if val is None or val == "":
        return None
    try:
        return float(str(val).replace(",", "."))
    except (ValueError, TypeError):
        return None


def _clean_dict(d: dict) -> dict:
    """Remover keys con valores None o strings vacíos."""
    if not isinstance(d, dict):
        return d
    return {
        k: _clean_dict(v) if isinstance(v, dict) else v
        for k, v in d.items()
        if v is not None and v != "" and (not isinstance(v, dict) or any(_clean_dict(v).values()))
    }
