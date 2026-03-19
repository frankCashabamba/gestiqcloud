from __future__ import annotations

from typing import Any

from .constants import INTERNAL_STRUCTURAL_KEYS
from .document_fields import (
    detect_document_currency,
    detect_document_date,
    detect_document_payment_method,
    detect_document_subtotal,
    detect_document_tax,
    detect_document_total,
    get_data_value,
)

CANONICAL_DOCUMENT_SCHEMA_VERSION = "importador.canonical.v1"


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _pick_line_items(
    data: dict[str, Any] | None,
    aliases: list[str] | None = None,
) -> list[dict[str, Any]]:
    keys = aliases or ["line_items", "items", "detalle", "filas_detalle"]
    raw = get_data_value(data, *keys)
    if not isinstance(raw, list):
        return []
    return [dict(entry) for entry in raw if isinstance(entry, dict)]


def build_canonical_document(
    data: dict[str, Any] | None,
    *,
    doc_type: str | None = None,
    source_format: str | None = None,
    field_aliases: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """
    Construye el documento canónico a partir de datos extraídos.
    Todos los aliases de campos se toman de field_aliases (cargado desde imp_field_alias en BD).
    Si field_aliases es None o vacío, los detectores de document_fields.py aplican sus propios
    defaults internos como fallback de último recurso.
    """
    payload: dict[str, Any] = {"schema_version": CANONICAL_DOCUMENT_SCHEMA_VERSION}
    if not isinstance(data, dict):
        return payload

    fa = field_aliases or {}

    vendor_name = _clean_text(
        get_data_value(data, *(fa.get("vendor") or []))
    )
    vendor_tax_id = _clean_text(
        get_data_value(data, *(fa.get("vendor_tax_id") or []))
    )
    customer_name = _clean_text(
        get_data_value(data, *(fa.get("customer") or []))
    )
    customer_tax_id = _clean_text(
        get_data_value(data, *(fa.get("customer_tax_id") or []))
    )
    doc_number = _clean_text(
        get_data_value(data, *(fa.get("doc_number") or []))
    )
    issue_date = detect_document_date(data, aliases=fa.get("issue_date") or None)
    subtotal = detect_document_subtotal(data, aliases=fa.get("subtotal") or None)
    tax_amount = detect_document_tax(data, aliases=fa.get("tax_amount") or None)
    total_amount = detect_document_total(data, aliases=fa.get("total_amount") or None)
    currency_code = _clean_text(detect_document_currency(data, aliases=fa.get("currency") or None))
    payment_method = _clean_text(detect_document_payment_method(data, aliases=fa.get("payment_method") or None))
    payment_terms = _clean_text(
        get_data_value(data, *(fa.get("payment_terms") or []))
    )
    line_items = _pick_line_items(data, aliases=fa.get("line_items") or None)

    payload["document"] = {
        "type": _clean_text(doc_type),
        "number": doc_number,
        "issue_date": issue_date,
        "source_format": _clean_text(source_format),
    }
    payload["vendor"] = {"name": vendor_name, "tax_id": vendor_tax_id}
    payload["customer"] = {"name": customer_name, "tax_id": customer_tax_id}
    payload["totals"] = {
        "subtotal": subtotal,
        "tax": tax_amount,
        "total": total_amount,
    }
    payload["currency"] = {"code": currency_code}
    payload["payments"] = {"method": payment_method, "terms": payment_terms}
    payload["line_items"] = line_items

    # El conjunto de campos "consumidos" se construye dinámicamente desde los aliases de BD.
    # Así, cualquier alias nuevo en imp_field_alias queda excluido de extensions automáticamente.
    consumed: set[str] = set(fa.keys())
    for aliases_list in fa.values():
        consumed.update(aliases_list)

    extensions = {
        str(key): value
        for key, value in data.items()
        if str(key) not in consumed
        and str(key) not in INTERNAL_STRUCTURAL_KEYS
        and not str(key).startswith("_")
    }
    if extensions:
        payload["extensions"] = extensions

    return payload


def build_document_projection(
    data: dict[str, Any] | None,
    *,
    doc_type: str | None = None,
    source_format: str | None = None,
    field_aliases: dict[str, list[str]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    canonical = build_canonical_document(
        data,
        doc_type=doc_type,
        source_format=source_format,
        field_aliases=field_aliases,
    )
    vendor = canonical.get("vendor") if isinstance(canonical.get("vendor"), dict) else {}
    document = canonical.get("document") if isinstance(canonical.get("document"), dict) else {}
    totals = canonical.get("totals") if isinstance(canonical.get("totals"), dict) else {}
    currency = canonical.get("currency") if isinstance(canonical.get("currency"), dict) else {}

    projection = {
        "proveedor_detectado": _clean_text(vendor.get("name")),
        "ruc_detectado": _clean_text(vendor.get("tax_id")),
        "monto_total": totals.get("total"),
        "moneda": _clean_text(currency.get("code")),
        "fecha_documento": _clean_text(document.get("issue_date")),
    }
    return canonical, projection
