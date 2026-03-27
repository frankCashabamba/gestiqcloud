from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.modules.importador.category_loader import classify_doc_type
from app.modules.importador.document_fields import safe_floatish
from app.modules.importador.schemas import DocumentRoutingDecision

SaveDestination = Literal["recipe", "expense", "supplier_invoice"]


@dataclass(frozen=True)
class RoutingProfile:
    document_type: str
    destination: SaveDestination | None
    required_groups: tuple[tuple[str, ...], ...]
    support_fields: tuple[str, ...]
    explanation_fields: tuple[str, ...]
    blocked: bool = False


FIELD_CANDIDATES: dict[str, tuple[str, ...]] = {
    "vendor": ("vendor", "supplier", "proveedor", "emisor", "supplier_name"),
    "vendor_tax_id": ("vendor_tax_id", "supplier_tax_id", "ruc", "tax_id", "nif", "vat"),
    "issue_date": ("issue_date", "invoice_date", "fecha", "date", "expense_date"),
    "due_date": ("due_date", "fecha_vencimiento", "payment_due_date"),
    "doc_number": ("doc_number", "invoice_number", "numero_factura", "reference", "folio"),
    "subtotal": ("subtotal", "base_amount", "amount_untaxed", "net_amount"),
    "tax_amount": ("tax_amount", "tax", "iva", "vat_amount", "impuesto"),
    "total_amount": ("total_amount", "monto_total", "total", "grand_total", "importe"),
    "currency": ("currency", "moneda", "divisa"),
    "payment_method": ("payment_method", "forma_pago", "metodo_pago", "payment_type"),
    "concept": ("concept", "description", "concepto", "detalle", "glosa"),
    "line_items": ("line_items", "lineas", "items"),
    "rows": ("filas", "filas_por_hoja"),
}

FIELD_LABELS: dict[str, str] = {
    "vendor": "proveedor",
    "vendor_tax_id": "identificacion fiscal",
    "issue_date": "fecha",
    "due_date": "vencimiento",
    "doc_number": "numero",
    "subtotal": "subtotal",
    "tax_amount": "impuesto",
    "total_amount": "total",
    "currency": "moneda",
    "payment_method": "forma de pago",
    "concept": "concepto",
    "line_items": "lineas",
    "rows": "filas",
}

ROUTING_PROFILES: dict[str, RoutingProfile] = {
    "supplier_invoice": RoutingProfile(
        document_type="supplier_invoice",
        destination="supplier_invoice",
        required_groups=(("vendor", "vendor_tax_id"), ("issue_date",), ("total_amount",)),
        support_fields=("subtotal", "tax_amount", "doc_number", "currency", "line_items"),
        explanation_fields=("vendor", "issue_date", "subtotal", "tax_amount", "total_amount"),
    ),
    "expense": RoutingProfile(
        document_type="expense",
        destination="expense",
        required_groups=(("issue_date",), ("total_amount",), ("concept", "vendor", "doc_number")),
        support_fields=("tax_amount", "currency", "payment_method"),
        explanation_fields=("concept", "vendor", "issue_date", "tax_amount", "total_amount"),
    ),
    "recipe": RoutingProfile(
        document_type="recipe",
        destination="recipe",
        required_groups=(("rows", "line_items"),),
        support_fields=("doc_number",),
        explanation_fields=("rows", "line_items"),
    ),
    "inventory": RoutingProfile(
        document_type="inventory",
        destination=None,
        required_groups=(("rows", "line_items"),),
        support_fields=("doc_number",),
        explanation_fields=("rows", "line_items"),
        blocked=True,
    ),
    "bank_statement": RoutingProfile(
        document_type="bank_statement",
        destination=None,
        required_groups=(("issue_date",), ("rows", "line_items")),
        support_fields=("currency",),
        explanation_fields=("issue_date", "rows"),
        blocked=True,
    ),
    "payroll": RoutingProfile(
        document_type="payroll",
        destination=None,
        required_groups=(("issue_date",), ("rows", "line_items")),
        support_fields=("total_amount",),
        explanation_fields=("issue_date", "rows", "total_amount"),
        blocked=True,
    ),
    "other": RoutingProfile(
        document_type="expense",
        destination="expense",
        required_groups=(("issue_date",), ("total_amount",)),
        support_fields=("concept", "vendor", "tax_amount"),
        explanation_fields=("concept", "vendor", "issue_date", "total_amount"),
    ),
}

CATEGORY_TO_PROFILE_KEY: dict[str, str] = {
    "invoice": "supplier_invoice",
    "receipt": "expense",
    "recipe": "recipe",
    "inventory": "inventory",
    "bank": "bank_statement",
    "payroll": "payroll",
}

DESTINATION_TO_PROFILE_KEY: dict[SaveDestination, str] = {
    "supplier_invoice": "supplier_invoice",
    "expense": "expense",
    "recipe": "recipe",
}


def _normalized_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _canonical_fields(canonical_document: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(canonical_document, dict):
        return {}
    fields = canonical_document.get("fields")
    return fields if isinstance(fields, dict) else {}


def _field_from_sources(
    field_name: str,
    *,
    extracted_data: dict[str, Any] | None,
    canonical_document: dict[str, Any] | None,
) -> Any:
    canonical_fields = _canonical_fields(canonical_document)
    if field_name in canonical_fields:
        return canonical_fields[field_name]

    source = extracted_data if isinstance(extracted_data, dict) else {}
    normalized_source = {str(key).strip().lower(): value for key, value in source.items()}
    for candidate in FIELD_CANDIDATES.get(field_name, (field_name,)):
        value = normalized_source.get(candidate.strip().lower())
        if value is not None:
            return value
    return None


def _has_value(
    field_name: str,
    *,
    extracted_data: dict[str, Any] | None,
    canonical_document: dict[str, Any] | None,
) -> bool:
    value = _field_from_sources(
        field_name,
        extracted_data=extracted_data,
        canonical_document=canonical_document,
    )
    if value is None:
        return False
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        if field_name in {"subtotal", "tax_amount", "total_amount"}:
            return safe_floatish(value) is not None
        return bool(value.strip())
    if isinstance(value, list):
        return len(value) > 0
    if isinstance(value, dict):
        return len(value) > 0
    return True


def _build_reason(
    profile: RoutingProfile,
    *,
    missing_fields: list[str],
    extracted_data: dict[str, Any] | None,
    canonical_document: dict[str, Any] | None,
) -> str:
    if missing_fields:
        readable = ", ".join(FIELD_LABELS.get(field, field) for field in missing_fields[:4])
        if profile.destination:
            return f"Faltan {readable} para guardar como {profile.document_type}."
        return f"Faltan {readable}; requiere revisión manual."

    found_fields = [
        FIELD_LABELS.get(field, field)
        for field in profile.explanation_fields
        if _has_value(
            field,
            extracted_data=extracted_data,
            canonical_document=canonical_document,
        )
    ]
    if found_fields:
        return f"Contiene {', '.join(found_fields[:5])}."
    if profile.blocked:
        return "Documento detectado fuera del guardado automatico; requiere revisión manual."
    return "Documento listo para revisión y guardado."


def _fallback_category(
    *,
    extracted_data: dict[str, Any] | None,
    canonical_document: dict[str, Any] | None,
) -> str:
    has_vendor = _has_value(
        "vendor",
        extracted_data=extracted_data,
        canonical_document=canonical_document,
    ) or _has_value(
        "vendor_tax_id",
        extracted_data=extracted_data,
        canonical_document=canonical_document,
    )
    has_total = _has_value(
        "total_amount",
        extracted_data=extracted_data,
        canonical_document=canonical_document,
    )
    has_rows = _has_value(
        "rows",
        extracted_data=extracted_data,
        canonical_document=canonical_document,
    ) or _has_value(
        "line_items",
        extracted_data=extracted_data,
        canonical_document=canonical_document,
    )
    if has_vendor and has_total:
        return "invoice"
    if has_rows:
        return "recipe"
    if has_total:
        return "receipt"
    return "other"


def _match_ratio(
    groups: tuple[tuple[str, ...], ...],
    *,
    extracted_data: dict[str, Any] | None,
    canonical_document: dict[str, Any] | None,
) -> tuple[int, list[str]]:
    matched = 0
    missing: list[str] = []
    for group in groups:
        if any(
            _has_value(
                field_name,
                extracted_data=extracted_data,
                canonical_document=canonical_document,
            )
            for field_name in group
        ):
            matched += 1
            continue
        missing.append(group[0])
    return matched, missing


def _support_ratio(
    fields: tuple[str, ...],
    *,
    extracted_data: dict[str, Any] | None,
    canonical_document: dict[str, Any] | None,
) -> float:
    if not fields:
        return 1.0
    matched = sum(
        1
        for field_name in fields
        if _has_value(
            field_name,
            extracted_data=extracted_data,
            canonical_document=canonical_document,
        )
    )
    return matched / len(fields)


def build_document_routing_decision(
    *,
    source_doc_type: str | None,
    ai_confidence: float | None,
    extracted_data: dict[str, Any] | None,
    canonical_document: dict[str, Any] | None,
    category_keywords: dict[str, list[str]] | None,
    requires_review: bool = False,
    destination_override: SaveDestination | None = None,
) -> DocumentRoutingDecision:
    source_label = _normalized_text(source_doc_type) or "OTHER"
    normalized_source = source_label.upper()
    category_map = category_keywords or {}
    source_category = classify_doc_type(normalized_source, category_map)
    if source_category == "other":
        source_category = _fallback_category(
            extracted_data=extracted_data,
            canonical_document=canonical_document,
        )

    profile_key = (
        DESTINATION_TO_PROFILE_KEY[destination_override]
        if destination_override is not None
        else CATEGORY_TO_PROFILE_KEY.get(source_category, "other")
    )
    profile = ROUTING_PROFILES[profile_key]
    matched_required, missing_fields = _match_ratio(
        profile.required_groups,
        extracted_data=extracted_data,
        canonical_document=canonical_document,
    )
    required_groups_total = max(len(profile.required_groups), 1)
    required_ratio = matched_required / required_groups_total
    support_ratio = _support_ratio(
        profile.support_fields,
        extracted_data=extracted_data,
        canonical_document=canonical_document,
    )

    safe_ai_confidence = max(0.0, min(1.0, float(ai_confidence or 0.0)))
    category_bonus = 1.0 if source_category != "other" else 0.72
    confidence = (
        (safe_ai_confidence * 0.6)
        + (required_ratio * 0.25)
        + (support_ratio * 0.1)
        + (category_bonus * 0.05)
    )
    if missing_fields:
        confidence = min(confidence, 0.79)
    profile_blocked = profile.blocked and destination_override is None
    if profile_blocked:
        confidence = min(confidence, 0.58)
    confidence = round(max(0.0, min(1.0, confidence)), 2)

    required_fields_ok = len(missing_fields) == 0
    needs_human_review = (
        requires_review
        or profile_blocked
        or not required_fields_ok
        or confidence < 0.8
    )

    return DocumentRoutingDecision(
        document_type=profile.document_type,
        confidence=confidence,
        required_fields_ok=required_fields_ok,
        missing_fields=missing_fields,
        suggested_destination=None if needs_human_review and profile_blocked else profile.destination,
        reason=_build_reason(
            profile,
            missing_fields=missing_fields,
            extracted_data=extracted_data,
            canonical_document=canonical_document,
        ),
        needs_human_review=needs_human_review,
        source_doc_type=normalized_source,
        source_category=source_category,
    )


def parse_document_routing_decision(raw_ai_json: dict[str, Any] | None) -> DocumentRoutingDecision | None:
    if not isinstance(raw_ai_json, dict):
        return None
    payload = raw_ai_json.get("routing")
    if not isinstance(payload, dict):
        return None
    try:
        return DocumentRoutingDecision.model_validate(payload)
    except Exception:
        return None
