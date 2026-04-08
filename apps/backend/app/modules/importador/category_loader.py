"""Loads document-type category keywords from the database.

Keywords live in imp_config (module='doc_categories').
Each row: key = category name (invoice/receipt/recipe/…), value_list = JSON array of keyword substrings.

Cache refreshes every 5 minutes. On DB failure falls back to a minimal hardcoded set
so the system degrades gracefully without crashing.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from .runtime_config import load_doc_categories_config

logger = logging.getLogger("importador.category_loader")

_CACHE_TTL = 300  # seconds

_cache: dict[str, list[str]] = {}
_cache_ts: float = 0.0


def get_doc_categories(db: Any) -> dict[str, list[str]]:
    """Return {category: [keyword, …]} loaded from DB, refreshed every 5 min."""
    global _cache, _cache_ts

    now = time.monotonic()
    if _cache and (now - _cache_ts) < _CACHE_TTL:
        return _cache

    try:
        result = load_doc_categories_config(db)
        if result:
            _cache = result
            _cache_ts = now
            return result
    except Exception as exc:
        logger.warning("Could not load doc categories from imp_config: %s", exc)

    return load_doc_categories_config(None)


def classify_doc_type(tipo: str, categories: dict[str, list[str]]) -> str:
    """Map a free-form doc_type string to an internal category name.

    Checks each category's keywords as substrings of tipo (uppercase).
    Returns the matched category or 'other'.
    """
    if not tipo:
        return "other"
    tipo_upper = tipo.strip().upper()
    for category, keywords in categories.items():
        if any(kw in tipo_upper for kw in keywords):
            return category
    return "other"
