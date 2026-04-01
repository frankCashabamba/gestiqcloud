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

logger = logging.getLogger("importador.category_loader")

_CACHE_TTL = 300  # seconds

_cache: dict[str, list[str]] = {}
_cache_ts: float = 0.0

# Minimal emergency defaults — used only when DB is unreachable.
# Add new categories via DB migration, not here.
_BUILTIN_FALLBACK: dict[str, list[str]] = {
    "invoice": ["INVOICE", "FACTURA", "CREDIT_NOTE", "PURCHASE_ORDER", "QUOTE", "PROFORMA"],
    "receipt": ["RECEIPT", "TICKET", "RECIBO", "BOLETA", "VOUCHER"],
    "recipe": ["COSTING", "COSTEO", "RECIPE", "RECETA"],
    "inventory": ["INVENTORY", "INVENTARIO", "PRICE_LIST", "LISTA_PRECIOS", "STOCK"],
    "bank": ["BANK_STATEMENT", "EXTRACTO_BANCARIO", "BANK_MOVEMENTS", "MOVIMIENTOS_BANCARIOS"],
    "payroll": ["PAYROLL", "NOMINA", "PLANILLA"],
}


def get_doc_categories(db: Any) -> dict[str, list[str]]:
    """Return {category: [keyword, …]} loaded from DB, refreshed every 5 min."""
    global _cache, _cache_ts

    now = time.monotonic()
    if _cache and (now - _cache_ts) < _CACHE_TTL:
        return _cache

    try:
        from app.models.importador import ImpConfig

        rows = db.query(ImpConfig).filter(ImpConfig.module == "doc_categories").all()
        if rows:
            result: dict[str, list[str]] = {}
            for row in rows:
                kws = row.value_list
                if isinstance(kws, list) and kws:
                    result[row.key] = [str(k).upper() for k in kws]
            if result:
                _cache = result
                _cache_ts = now
                return result
    except Exception as exc:
        logger.warning("Could not load doc categories from imp_config: %s", exc)

    return _BUILTIN_FALLBACK


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
