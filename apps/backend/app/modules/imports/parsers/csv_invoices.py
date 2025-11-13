"""
Parser para facturas en formato CSV.

Espera columnas estándar: invoice_number, invoice_date, vendor, vendor_tax_id,
buyer, buyer_tax_id, subtotal, tax, total, currency, payment_method, etc.

Salida: lista de CanonicalDocument con doc_type='invoice'
"""

import csv
from typing import Any


def parse_csv_invoices(file_path: str) -> dict[str, Any]:
    """
    Parse CSV file with invoice data.

    Args:
        file_path: Path to CSV file

    Returns:
        Dict with 'invoices' list and metadata
    """
    invoices = []
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

                # Extraer campos canónicos
                invoice = {
                    "doc_type": "invoice",
                    "invoice_number": (
                        normalized_row.get("invoice_number")
                        or normalized_row.get("numero")
                        or normalized_row.get("numero_factura")
                        or f"CSV-INV-{idx}"
                    ),
                    "issue_date": (
                        normalized_row.get("issue_date")
                        or normalized_row.get("invoice_date")
                        or normalized_row.get("fecha_emision")
                        or normalized_row.get("fecha")
                    ),
                    "due_date": (
                        normalized_row.get("due_date") or normalized_row.get("fecha_vencimiento")
                    ),
                    "vendor": {
                        "name": (
                            normalized_row.get("vendor")
                            or normalized_row.get("vendor_name")
                            or normalized_row.get("proveedor")
                        ),
                        "tax_id": (
                            normalized_row.get("vendor_tax_id")
                            or normalized_row.get("vendor_ruc")
                            or normalized_row.get("ruc")
                        ),
                        "country": (
                            normalized_row.get("vendor_country")
                            or normalized_row.get("country")
                            or "EC"
                        ),
                    },
                    "buyer": {
                        "name": (
                            normalized_row.get("buyer")
                            or normalized_row.get("buyer_name")
                            or normalized_row.get("cliente")
                        ),
                        "tax_id": (
                            normalized_row.get("buyer_tax_id") or normalized_row.get("buyer_ruc")
                        ),
                    },
                    "currency": (
                        normalized_row.get("currency") or normalized_row.get("moneda") or "USD"
                    ),
                    "totals": {
                        "subtotal": _to_float(normalized_row.get("subtotal")),
                        "tax": _to_float(normalized_row.get("tax") or normalized_row.get("iva")),
                        "total": _to_float(
                            normalized_row.get("total") or normalized_row.get("amount")
                        ),
                    },
                    "payment": {
                        "method": (
                            normalized_row.get("payment_method")
                            or normalized_row.get("forma_pago")
                            or "cash"
                        ),
                        "reference": (
                            normalized_row.get("payment_reference")
                            or normalized_row.get("referencia_pago")
                        ),
                    },
                    "source": "csv",
                    "confidence": 0.8,
                    "_metadata": {
                        "parser": "csv_invoices",
                        "row_index": idx,
                    },
                }

                # Limpiar nulos
                invoice = _clean_dict(invoice)
                invoices.append(invoice)

    except Exception as e:
        errors.append(str(e))

    return {
        "invoices": invoices,
        "rows_processed": rows_processed,
        "rows_parsed": len(invoices),
        "errors": errors,
        "source_type": "csv",
        "parser": "csv_invoices",
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
