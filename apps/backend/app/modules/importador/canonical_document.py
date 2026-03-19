from __future__ import annotations

from typing import Any

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

_SYSTEM_KEYS = {
    "filas",
    "total_filas",
    "columnas",
    "columnas_norm",
    "hojas",
    "sheet_usada",
    "metadata",
    "metadata_por_hoja",
    "filas_por_hoja",
    "filas_por_hoja_count",
    "perfiles_hojas",
}


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _pick_line_items(data: dict[str, Any] | None) -> list[dict[str, Any]]:
    raw = get_data_value(data, "line_items", "items", "detalle", "filas_detalle")
    if not isinstance(raw, list):
        return []
    items: list[dict[str, Any]] = []
    for entry in raw:
        if isinstance(entry, dict):
            items.append(dict(entry))
    return items


def build_canonical_document(
    data: dict[str, Any] | None,
    *,
    doc_type: str | None = None,
    source_format: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"schema_version": CANONICAL_DOCUMENT_SCHEMA_VERSION}
    if not isinstance(data, dict):
        return payload

    vendor_name = _clean_text(
        get_data_value(data, "vendor", "vendor_name", "supplier", "proveedor", "emisor")
    )
    vendor_tax_id = _clean_text(
        get_data_value(data, "vendor_tax_id", "supplier_tax_id", "tax_id", "ruc", "ruc_proveedor")
    )
    customer_name = _clean_text(get_data_value(data, "customer", "customer_name", "cliente"))
    customer_tax_id = _clean_text(
        get_data_value(data, "customer_tax_id", "client_tax_id", "ruc_cliente")
    )
    doc_number = _clean_text(
        get_data_value(
            data,
            "document_number",
            "doc_number",
            "invoice_number",
            "numero_documento",
            "numero_factura",
            "numero",
        )
    )
    issue_date = detect_document_date(data)
    subtotal = detect_document_subtotal(data)
    tax_amount = detect_document_tax(data)
    total_amount = detect_document_total(data)
    currency_code = _clean_text(detect_document_currency(data))
    payment_method = _clean_text(detect_document_payment_method(data))
    payment_terms = _clean_text(
        get_data_value(
            data,
            "payment_terms",
            "terms_of_payment",
            "condiciones_pago",
            "condicion_pago",
        )
    )
    line_items = _pick_line_items(data)

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

    consumed = {
        "vendor",
        "vendor_name",
        "supplier",
        "proveedor",
        "emisor",
        "vendor_tax_id",
        "supplier_tax_id",
        "tax_id",
        "ruc",
        "ruc_proveedor",
        "customer",
        "customer_name",
        "cliente",
        "customer_tax_id",
        "client_tax_id",
        "ruc_cliente",
        "document_number",
        "doc_number",
        "invoice_number",
        "numero_documento",
        "numero_factura",
        "numero",
        "issue_date",
        "fecha",
        "date",
        "invoice_date",
        "expense_date",
        "subtotal",
        "base_imponible",
        "neto",
        "monto",
        "amount_before_tax",
        "tax_amount",
        "iva",
        "tax",
        "vat",
        "impuesto",
        "igv",
        "total_amount",
        "monto_total",
        "total",
        "amount",
        "importe",
        "grand_total",
        "total_general",
        "currency",
        "moneda",
        "divisa",
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
        "line_items",
        "items",
        "detalle",
        "filas_detalle",
    }
    extensions = {
        str(key): value
        for key, value in data.items()
        if str(key) not in consumed and str(key) not in _SYSTEM_KEYS and not str(key).startswith("_")
    }
    if extensions:
        payload["extensions"] = extensions

    return payload


def build_document_projection(
    data: dict[str, Any] | None,
    *,
    doc_type: str | None = None,
    source_format: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    canonical = build_canonical_document(data, doc_type=doc_type, source_format=source_format)
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
