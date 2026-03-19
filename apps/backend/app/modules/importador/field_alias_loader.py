"""Carga aliases de campos canónicos desde la base de datos.

Los aliases viven en imp_field_alias (tenant_id=NULL para globales).
Caché de 5 minutos. Fallback mínimo de emergencia si la BD falla.
Replicar el patrón de category_loader.py.

Campos canónicos soportados:
  total_amount, subtotal, tax_amount, issue_date, vendor, vendor_tax_id,
  customer, customer_tax_id, doc_number, currency, payment_method,
  payment_terms, line_items
"""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

logger = logging.getLogger("importador.field_alias_loader")

_CACHE_TTL = 300  # segundos

_cache: dict[str, list[str]] = {}
_cache_ts: float = 0.0

# Fallback mínimo de emergencia — se usan solo si la BD es inalcanzable.
# La fuente de verdad son los registros en imp_field_alias.
_BUILTIN_FALLBACK: dict[str, list[str]] = {
    "total_amount":   ["total_amount", "monto_total", "total", "amount",
                       "importe", "grand_total", "total_general"],
    "subtotal":       ["subtotal", "base_imponible", "neto", "monto",
                       "amount_before_tax"],
    "tax_amount":     ["tax_amount", "iva", "tax", "vat", "impuesto", "igv"],
    "issue_date":     ["issue_date", "fecha", "date", "invoice_date",
                       "expense_date"],
    "currency":       ["currency", "moneda", "divisa"],
    "vendor":         ["vendor", "vendor_name", "supplier", "proveedor",
                       "emisor", "issuer"],
    "vendor_tax_id":  ["vendor_tax_id", "supplier_tax_id", "tax_id",
                       "ruc", "ruc_proveedor"],
    "customer":       ["customer", "customer_name", "cliente"],
    "customer_tax_id": ["customer_tax_id", "client_tax_id", "ruc_cliente"],
    "doc_number":     ["doc_number", "document_number", "invoice_number",
                       "numero_documento", "numero_factura", "numero"],
    "payment_method": ["payment_method", "payment_type", "payment_mode",
                       "metodo_pago", "metodo_de_pago", "forma_pago",
                       "forma_de_pago", "tipo_pago", "tipo_de_pago",
                       "medio_pago", "medio_de_pago"],
    "payment_terms":  ["payment_terms", "terms_of_payment",
                       "condicion_pago", "condiciones_pago"],
    "line_items":     ["line_items", "items", "detalle", "filas_detalle"],
}


def get_field_aliases(
    db: Any,
    *,
    tenant_id: UUID | None = None,
) -> dict[str, list[str]]:
    """Retorna {campo_canonico: [alias, ...]} desde BD, caché 5 min."""
    global _cache, _cache_ts

    now = time.monotonic()
    if _cache and (now - _cache_ts) < _CACHE_TTL:
        return _cache

    try:
        from sqlalchemy import text as sa_text

        rows = db.execute(
            sa_text(
                """
                SELECT canonical_field, alias
                FROM imp_field_alias
                WHERE active = TRUE
                  AND (tenant_id IS NULL OR tenant_id = :tid)
                ORDER BY priority DESC, canonical_field, alias
                """
            ),
            {"tid": str(tenant_id) if tenant_id else None},
        ).fetchall()

        if rows:
            result: dict[str, list[str]] = {}
            for row in rows:
                field = str(row[0] or "").strip()
                alias = str(row[1] or "").strip()
                if field and alias:
                    result.setdefault(field, [])
                    if alias not in result[field]:
                        result[field].append(alias)
            if result:
                _cache = result
                _cache_ts = now
                return result
    except Exception as exc:
        logger.warning("Could not load field aliases from DB: %s", exc)

    return _BUILTIN_FALLBACK


def get_aliases_for_field(
    db: Any,
    field: str,
    *,
    tenant_id: UUID | None = None,
) -> list[str]:
    """Retorna la lista de aliases para un campo canónico específico."""
    aliases = get_field_aliases(db, tenant_id=tenant_id)
    return aliases.get(field, _BUILTIN_FALLBACK.get(field, [field]))


def invalidate_cache() -> None:
    """Fuerza recarga desde BD en la próxima llamada."""
    global _cache_ts
    _cache_ts = 0.0
