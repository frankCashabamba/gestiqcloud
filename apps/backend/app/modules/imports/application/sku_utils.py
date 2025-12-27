"""Helpers for SKU normalization during imports."""

from typing import Any


def sanitize_sku(value: Any) -> str | None:
    """Normalize SKU to a trimmed string without altering its content."""
    if value is None:
        return None
    sku = str(value).strip()
    return sku or None
