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


def _extract_line_items(data: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    raw = data.get("line_items")
    if not isinstance(raw, list):
        return []
    return [row for row in raw if isinstance(row, dict)]


def _line_total(row: dict[str, Any]) -> float | None:
    direct_total = get_data_value(row, "total_price")
    total = safe_floatish(direct_total)
    if total is not None:
        return total

    quantity = safe_floatish(get_data_value(row, "quantity"))
    unit_price = safe_floatish(get_data_value(row, "unit_price"))
    if quantity is None or unit_price is None:
        return None
    return round(quantity * unit_price, 2)


def infer_total_from_line_items(data: dict[str, Any] | None) -> float | None:
    line_items = _extract_line_items(data)
    if not line_items:
        return None

    totals = []
    for row in line_items:
        total = _line_total(row)
        if total is not None:
            totals.append(total)

    if not totals:
        return None
    return round(sum(totals), 2)


def detect_document_total(
    data: dict[str, Any] | None,
    aliases: list[str] | None = None,
) -> float | None:
    direct_total = safe_floatish(get_data_value(data, *(aliases or [])))
    if direct_total is not None:
        return direct_total
    return infer_total_from_line_items(data)


def detect_document_subtotal(
    data: dict[str, Any] | None,
    aliases: list[str] | None = None,
) -> float | None:
    if not aliases:
        return None
    return safe_floatish(get_data_value(data, *aliases))


def detect_document_tax(
    data: dict[str, Any] | None,
    aliases: list[str] | None = None,
) -> float | None:
    if not aliases:
        return None
    return safe_floatish(get_data_value(data, *aliases))


def detect_document_currency(
    data: dict[str, Any] | None,
    aliases: list[str] | None = None,
) -> str | None:
    if not aliases:
        return None
    value = get_data_value(data, *aliases)
    return str(value).strip() if value is not None else None


def detect_document_payment_method(
    data: dict[str, Any] | None,
    aliases: list[str] | None = None,
) -> str | None:
    if not aliases:
        return None
    value = get_data_value(data, *aliases)
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
    if not aliases:
        return None
    value = get_data_value(data, *aliases)
    if value is None:
        return None
    s = str(value).strip()[:20]
    if "T" in s:
        s = s.split("T")[0]
    return s or None
