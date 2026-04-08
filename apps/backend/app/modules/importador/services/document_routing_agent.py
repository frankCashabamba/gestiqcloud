from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.importador.category_loader import classify_doc_type
from app.modules.importador.document_fields import detect_document_total, safe_floatish
from app.modules.importador.runtime_config import (
    load_routing_field_aliases,
    load_routing_field_labels,
    load_routing_scoring_config,
)
from app.modules.importador.schemas import DocumentRoutingDecision

from .document_routing_config import (
    RoutingProfileConfig,
    SaveDestination,
    invalidate_document_routing_cache,
    resolve_routing_profile,
    resolve_routing_profile_match,
)


def _field_candidates() -> dict[str, tuple[str, ...]]:
    return load_routing_field_aliases(None)


def _field_labels() -> dict[str, str]:
    return load_routing_field_labels(None)


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
    field_candidates = _field_candidates()
    for candidate in field_candidates.get(field_name, (field_name,)):
        value = normalized_source.get(candidate.strip().lower())
        if value is not None:
            return value
    if field_name == "total_amount":
        return detect_document_total(
            source, aliases=list(field_candidates.get("total_amount", ("total_amount",)))
        )
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
    profile: RoutingProfileConfig,
    *,
    missing_fields: list[str],
    extracted_data: dict[str, Any] | None,
    canonical_document: dict[str, Any] | None,
) -> str:
    if missing_fields:
        field_labels = _field_labels()
        readable = ", ".join(field_labels.get(field, field) for field in missing_fields[:4])
        if profile.suggested_destination:
            return f"Faltan {readable} para guardar como {profile.document_type}."
        return f"Faltan {readable}; requiere revision manual."

    field_labels = _field_labels()
    found_fields = [
        field_labels.get(field, field)
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
        return "Documento detectado fuera del guardado automatico; requiere revision manual."
    return "Documento listo para revision y guardado."


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
    source_category_override: str | None = None,
    ai_confidence: float | None,
    extracted_data: dict[str, Any] | None,
    canonical_document: dict[str, Any] | None,
    category_keywords: dict[str, list[str]] | None,
    requires_review: bool = False,
    destination_override: SaveDestination | None = None,
    db: Session | None = None,
    tenant_id: UUID | str | None = None,
    sector_override: str | None = None,
) -> DocumentRoutingDecision:
    source_label = _normalized_text(source_doc_type) or "OTHER"
    normalized_source = source_label.upper()
    category_map = category_keywords or {}
    source_category = (_normalized_text(source_category_override) or "").strip().lower()
    if not source_category:
        source_category = classify_doc_type(normalized_source, category_map)
    profile, _matched_by = resolve_routing_profile(
        db=db,
        tenant_id=tenant_id,
        sector_override=sector_override,
        source_doc_type=normalized_source,
        source_category=source_category,
        destination_override=destination_override,
    )

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

    scoring = load_routing_scoring_config(db)
    safe_ai_confidence = max(0.0, min(1.0, float(ai_confidence or 0.0)))
    category_bonus = (
        1.0 if source_category != "other" else float(scoring.get("other_category_bonus") or 0.72)
    )
    confidence = (
        (safe_ai_confidence * float(scoring.get("ai_confidence_weight") or 0.6))
        + (required_ratio * float(scoring.get("required_ratio_weight") or 0.25))
        + (support_ratio * float(scoring.get("support_ratio_weight") or 0.1))
        + (category_bonus * float(scoring.get("category_bonus_weight") or 0.05))
    )
    if missing_fields:
        confidence = min(confidence, max(profile.confidence_threshold - 0.01, 0.0))

    profile_blocked = profile.blocked and destination_override is None
    if profile_blocked:
        confidence = min(confidence, float(scoring.get("blocked_confidence_cap") or 0.58))
    confidence = round(max(0.0, min(1.0, confidence)), 2)

    required_fields_ok = len(missing_fields) == 0
    needs_human_review = (
        requires_review
        or profile_blocked
        or not required_fields_ok
        or confidence < profile.confidence_threshold
    )

    return DocumentRoutingDecision(
        document_type=profile.document_type,
        confidence=confidence,
        required_fields_ok=required_fields_ok,
        missing_fields=missing_fields,
        suggested_destination=(
            None if needs_human_review and profile_blocked else profile.suggested_destination
        ),
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


def parse_document_routing_decision(
    raw_ai_json: dict[str, Any] | None
) -> DocumentRoutingDecision | None:
    if not isinstance(raw_ai_json, dict):
        return None
    payload = raw_ai_json.get("routing")
    if not isinstance(payload, dict):
        return None
    try:
        return DocumentRoutingDecision.model_validate(payload)
    except Exception:
        return None


__all__ = [
    "build_document_routing_decision",
    "invalidate_document_routing_cache",
    "parse_document_routing_decision",
    "resolve_routing_profile_match",
]
