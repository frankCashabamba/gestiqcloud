from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.importador.category_loader import classify_doc_type
from app.modules.importador.destination_registry import load_destination_registry
from app.modules.importador.document_fields import detect_document_total, safe_floatish
from app.modules.importador.runtime_config import (
    load_routing_field_aliases,
    load_routing_field_labels,
    load_routing_scoring_config,
)
from app.modules.importador.schemas import (
    DestinationCapabilitiesOut,
    DocumentCandidateDestinationOut,
    DocumentRoutingDecision,
)

from .document_routing_config import (
    RoutingProfileConfig,
    SaveDestination,
    invalidate_document_routing_cache,
    resolve_routing_profile,
    resolve_routing_profile_match,
)

logger = logging.getLogger(__name__)

_SAVE_DOCUMENT_DESTINATIONS: tuple[SaveDestination, ...] = (
    "recipe",
    "expense",
    "supplier_invoice",
)


def _normalize_extracted_data(extracted_data: dict[str, Any] | None) -> dict[str, Any]:
    """Normaliza las claves del dict extraido UNA SOLA vez por decision."""
    if not isinstance(extracted_data, dict):
        return {}
    return {str(key).strip().lower(): value for key, value in extracted_data.items()}


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
    normalized_source: dict[str, Any] | None = None,
) -> Any:
    canonical_fields = _canonical_fields(canonical_document)
    if field_name in canonical_fields:
        return canonical_fields[field_name]

    source = extracted_data if isinstance(extracted_data, dict) else {}
    if normalized_source is None:
        normalized_source = _normalize_extracted_data(source)
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
    normalized_source: dict[str, Any] | None = None,
) -> bool:
    value = _field_from_sources(
        field_name,
        extracted_data=extracted_data,
        canonical_document=canonical_document,
        normalized_source=normalized_source,
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
    normalized_source: dict[str, Any] | None = None,
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
            normalized_source=normalized_source,
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
    normalized_source: dict[str, Any] | None = None,
) -> tuple[int, list[str]]:
    matched = 0
    missing: list[str] = []
    for group in groups:
        if any(
            _has_value(
                field_name,
                extracted_data=extracted_data,
                canonical_document=canonical_document,
                normalized_source=normalized_source,
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
    normalized_source: dict[str, Any] | None = None,
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
            normalized_source=normalized_source,
        )
    )
    return matched / len(fields)


def _evaluate_profile_state(
    profile: RoutingProfileConfig,
    *,
    ai_confidence: float | None,
    source_category: str,
    extracted_data: dict[str, Any] | None,
    canonical_document: dict[str, Any] | None,
    requires_review: bool = False,
    normalized_extracted_data: dict[str, Any] | None = None,
    scoring: dict[str, Any] | None = None,
    profile_blocked: bool | None = None,
) -> dict[str, Any]:
    normalized_source = normalized_extracted_data or _normalize_extracted_data(extracted_data)
    matched_required, missing_fields = _match_ratio(
        profile.required_groups,
        extracted_data=extracted_data,
        canonical_document=canonical_document,
        normalized_source=normalized_source,
    )
    required_groups_total = max(len(profile.required_groups), 1)
    required_ratio = matched_required / required_groups_total
    support_ratio = _support_ratio(
        profile.support_fields,
        extracted_data=extracted_data,
        canonical_document=canonical_document,
        normalized_source=normalized_source,
    )

    scoring_cfg = scoring or load_routing_scoring_config(None)
    safe_ai_confidence = max(0.0, min(1.0, float(ai_confidence or 0.0)))
    category_bonus = (
        1.0
        if source_category != "other"
        else float(scoring_cfg.get("other_category_bonus") or 0.72)
    )
    confidence = (
        (safe_ai_confidence * float(scoring_cfg.get("ai_confidence_weight") or 0.6))
        + (required_ratio * float(scoring_cfg.get("required_ratio_weight") or 0.25))
        + (support_ratio * float(scoring_cfg.get("support_ratio_weight") or 0.1))
        + (category_bonus * float(scoring_cfg.get("category_bonus_weight") or 0.05))
    )
    if missing_fields:
        confidence = min(confidence, max(profile.confidence_threshold - 0.01, 0.0))

    blocked = profile.blocked if profile_blocked is None else profile_blocked
    if blocked:
        confidence = min(confidence, float(scoring_cfg.get("blocked_confidence_cap") or 0.58))
    confidence = round(max(0.0, min(1.0, confidence)), 2)

    required_fields_ok = len(missing_fields) == 0
    needs_human_review = (
        requires_review
        or blocked
        or not required_fields_ok
        or confidence < profile.confidence_threshold
    )

    return {
        "confidence": confidence,
        "required_fields_ok": required_fields_ok,
        "missing_fields": missing_fields,
        "needs_human_review": needs_human_review,
        "reason": _build_reason(
            profile,
            missing_fields=missing_fields,
            extracted_data=extracted_data,
            canonical_document=canonical_document,
            normalized_source=normalized_source,
        ),
    }


def _destination_matches_profile(
    entry,
    *,
    profile: RoutingProfileConfig,
    source_category: str,
) -> bool:
    allowed_document_types = {
        str(item).strip().lower()
        for item in getattr(entry, "compatible_document_types", ())
        if str(item).strip()
    }
    allowed_source_categories = {
        str(item).strip().lower()
        for item in getattr(entry, "compatible_source_categories", ())
        if str(item).strip()
    }
    document_type = str(profile.document_type or "").strip().lower()
    if document_type and document_type in allowed_document_types:
        return True
    if source_category and source_category in allowed_source_categories:
        return True
    if (
        profile.suggested_destination
        and str(profile.suggested_destination).strip().lower() == str(entry.code).strip().lower()
    ):
        return True
    return False


def _build_candidate_destinations(
    *,
    profile: RoutingProfileConfig,
    source_doc_type: str | None,
    source_category: str,
    ai_confidence: float | None,
    extracted_data: dict[str, Any] | None,
    canonical_document: dict[str, Any] | None,
    requires_review: bool,
    db: Session | None,
    tenant_id: UUID | str | None,
    sector_override: str | None,
    normalized_extracted_data: dict[str, Any],
    scoring: dict[str, Any],
) -> list[DocumentCandidateDestinationOut]:
    registry = load_destination_registry(db)
    candidates: list[DocumentCandidateDestinationOut] = []
    preferred_code = str(profile.suggested_destination or "").strip().lower()

    for entry in sorted(registry.values(), key=lambda item: item.save_order):
        if not entry.enabled or not entry.include_in_candidates:
            continue
        if not _destination_matches_profile(
            entry,
            profile=profile,
            source_category=source_category,
        ):
            continue

        if entry.code in _SAVE_DOCUMENT_DESTINATIONS:
            candidate_profile, _matched_by = resolve_routing_profile(
                db=db,
                tenant_id=tenant_id,
                sector_override=sector_override,
                source_doc_type=source_doc_type,
                source_category=source_category,
                destination_override=entry.code,
            )
            state = _evaluate_profile_state(
                candidate_profile,
                ai_confidence=ai_confidence,
                source_category=source_category,
                extracted_data=extracted_data,
                canonical_document=canonical_document,
                requires_review=requires_review,
                normalized_extracted_data=normalized_extracted_data,
                scoring=scoring,
                profile_blocked=False,
            )
        else:
            state = _evaluate_profile_state(
                profile,
                ai_confidence=ai_confidence,
                source_category=source_category,
                extracted_data=extracted_data,
                canonical_document=canonical_document,
                requires_review=requires_review,
                normalized_extracted_data=normalized_extracted_data,
                scoring=scoring,
                profile_blocked=bool(profile.blocked),
            )

        candidates.append(
            DocumentCandidateDestinationOut(
                code=entry.code,
                label=entry.label,
                target=entry.target,
                target_tables=list(entry.target_tables),
                save_api=entry.save_api,
                score=state["confidence"],
                save_ready=bool(state["required_fields_ok"])
                and not bool(state["needs_human_review"]),
                required_fields_ok=bool(state["required_fields_ok"]),
                missing_fields=list(state["missing_fields"]),
                needs_human_review=bool(state["needs_human_review"]),
                reason=str(state["reason"]),
                confirmation_required=bool(entry.confirmation_required),
                capabilities=DestinationCapabilitiesOut(
                    supports_update_stock=entry.capabilities.supports_update_stock,
                    supports_line_matching=entry.capabilities.supports_line_matching,
                    supports_partial_payment=entry.capabilities.supports_partial_payment,
                    supports_multi_record_save=entry.capabilities.supports_multi_record_save,
                ),
            )
        )

    return sorted(
        candidates,
        key=lambda item: (
            not item.save_ready,
            item.code != preferred_code,
            -item.score,
            item.code,
        ),
    )


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

    # Pre-computar una sola vez por decision para evitar reconstruir el dict
    # normalizado en cada llamada a _field_from_sources / _has_value.
    normalized_extracted_data = _normalize_extracted_data(extracted_data)

    scoring = load_routing_scoring_config(db)
    profile_blocked = profile.blocked and destination_override is None
    state = _evaluate_profile_state(
        profile,
        ai_confidence=ai_confidence,
        source_category=source_category,
        extracted_data=extracted_data,
        canonical_document=canonical_document,
        requires_review=requires_review,
        normalized_extracted_data=normalized_extracted_data,
        scoring=scoring,
        profile_blocked=profile_blocked,
    )
    candidate_destinations = _build_candidate_destinations(
        profile=profile,
        source_doc_type=normalized_source,
        source_category=source_category,
        ai_confidence=ai_confidence,
        extracted_data=extracted_data,
        canonical_document=canonical_document,
        requires_review=requires_review,
        db=db,
        tenant_id=tenant_id,
        sector_override=sector_override,
        normalized_extracted_data=normalized_extracted_data,
        scoring=scoring,
    )
    primary_destination = next(
        (
            candidate.code
            for candidate in candidate_destinations
            if candidate.save_ready and candidate.code == profile.suggested_destination
        ),
        None,
    ) or next(
        (candidate.code for candidate in candidate_destinations if candidate.save_ready),
        None,
    )

    return DocumentRoutingDecision(
        document_type=profile.document_type,
        confidence=state["confidence"],
        required_fields_ok=state["required_fields_ok"],
        missing_fields=state["missing_fields"],
        suggested_destination=(
            None
            if state["needs_human_review"] and profile_blocked
            else profile.suggested_destination
        ),
        primary_destination=primary_destination,
        candidate_destinations=candidate_destinations,
        reason=state["reason"],
        needs_human_review=state["needs_human_review"],
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
    except Exception as e:
        logger.warning(f"[routing] Error parseando routing_decision: {e!r}")
        return None


__all__ = [
    "build_document_routing_decision",
    "invalidate_document_routing_cache",
    "parse_document_routing_decision",
    "resolve_routing_profile_match",
]
