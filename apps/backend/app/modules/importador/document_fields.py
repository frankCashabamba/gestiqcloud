from __future__ import annotations

import re
from typing import Any


def get_data_value(data: dict[str, Any] | None, *keys: str) -> Any:
    if not isinstance(data, dict):
        return None

    normalized: dict[str, Any] = {}
    for raw_key, value in data.items():
        key = str(raw_key or "").strip().lower()
        if key and key not in normalized:
            normalized[key] = value

    for raw_key in keys:
        key = str(raw_key or "").strip().lower()
        if not key:
            continue
        value = normalized.get(key)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def safe_floatish(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)

    raw = str(value or "").strip()
    if not raw:
        return None

    cleaned = re.sub(r"[^0-9,.\-]", "", raw.replace("\xa0", " "))
    if not cleaned or cleaned in {"-", ".", ","}:
        return None

    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned and "." not in cleaned:
        cleaned = cleaned.replace(",", ".")

    try:
        return float(cleaned)
    except (TypeError, ValueError):
        return None


def detect_document_total(
    data: dict[str, Any] | None,
    aliases: list[str] | None = None,
) -> float | None:
    keys = aliases or [
        "total_amount", "monto_total", "total", "amount",
        "importe", "grand_total", "total_general",
    ]
    return safe_floatish(get_data_value(data, *keys))


def detect_document_subtotal(
    data: dict[str, Any] | None,
    aliases: list[str] | None = None,
) -> float | None:
    keys = aliases or ["subtotal", "base_imponible", "neto", "monto", "amount_before_tax"]
    return safe_floatish(get_data_value(data, *keys))


def detect_document_tax(
    data: dict[str, Any] | None,
    aliases: list[str] | None = None,
) -> float | None:
    keys = aliases or ["tax_amount", "iva", "tax", "vat", "impuesto", "igv"]
    return safe_floatish(get_data_value(data, *keys))


def detect_document_currency(
    data: dict[str, Any] | None,
    aliases: list[str] | None = None,
) -> str | None:
    keys = aliases or ["moneda", "currency", "divisa"]
    value = get_data_value(data, *keys)
    return str(value).strip() if value is not None else None


def detect_document_payment_method(
    data: dict[str, Any] | None,
    aliases: list[str] | None = None,
) -> str | None:
    keys = aliases or [
        "payment_method",
        "payment_type",
        "payment_terms",
        "payment_mode",
        "metodo_pago",
        "metodo_de_pago",
        "forma_pago",
        "forma_de_pago",
        "tipo_pago",
        "tipo_de_pago",
        "medio_pago",
        "medio_de_pago",
        "condicion_pago",
        "condiciones_pago",
        "terms_of_payment",
    ]
    value = get_data_value(data, *keys)
    if isinstance(value, list):
        tokens = [str(item).strip() for item in value if str(item).strip()]
        return ", ".join(tokens) if tokens else None
    if isinstance(value, dict):
        for candidate_key in ("name", "label", "value", "description", "method", "type"):
            candidate = value.get(candidate_key)
            if candidate is None:
                continue
            text = str(candidate).strip()
            if text:
                return text
        return None
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def detect_document_date(
    data: dict[str, Any] | None,
    aliases: list[str] | None = None,
) -> str | None:
    keys = aliases or ["issue_date", "fecha", "date", "invoice_date", "expense_date"]
    value = get_data_value(data, *keys)
    if value is None:
        return None
    s = str(value).strip()[:20]
    if "T" in s:
        s = s.split("T")[0]
    return s or None
