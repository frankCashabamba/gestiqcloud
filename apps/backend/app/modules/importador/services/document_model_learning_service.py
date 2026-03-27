from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy.orm import Session

from app.models.importador import ImpDocumento, ImpRoutingSignal


_INTERNAL_KEYS = {
    "line_items",
    "rows",
    "_save",
}


def _is_scalar(value: Any) -> bool:
    return value is not None and not isinstance(value, (dict, list, tuple, set, bool))


def _normalize_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _signal_source_doc_type(signal: ImpRoutingSignal, doc: ImpDocumento) -> str:
    snapshot = signal.routing_snapshot if isinstance(signal.routing_snapshot, dict) else {}
    raw = snapshot.get("source_doc_type") or getattr(doc, "tipo_documento_detectado", None) or "OTHER"
    return str(raw).strip().upper() or "OTHER"


def _signal_document_type(signal: ImpRoutingSignal) -> str:
    snapshot = signal.routing_snapshot if isinstance(signal.routing_snapshot, dict) else {}
    raw = snapshot.get("document_type") or signal.chosen_destination or "other"
    return str(raw).strip().lower() or "other"


def _event_weight(event: str) -> float:
    normalized = str(event or "").strip().lower()
    if normalized == "save":
        return 4.0
    if normalized == "confirm":
        return 3.0
    if normalized == "edit":
        return 1.35
    return 1.0


def _signal_quality_weight(signal: ImpRoutingSignal) -> float:
    snapshot = signal.routing_snapshot if isinstance(signal.routing_snapshot, dict) else {}
    weight = _event_weight(signal.event)
    if bool(snapshot.get("required_fields_ok")):
        weight += 0.75
    if not bool(snapshot.get("needs_human_review")):
        weight += 0.45
    if str(signal.chosen_destination or "").strip():
        weight += 0.35
    return weight


def _signal_matches(
    signal: ImpRoutingSignal,
    doc: ImpDocumento,
    *,
    source_doc_type: str | None,
    document_type_hint: str | None,
) -> bool:
    wanted_source = str(source_doc_type or "").strip().upper()
    wanted_document_type = str(document_type_hint or "").strip().lower()
    if wanted_source and _signal_source_doc_type(signal, doc) != wanted_source:
        return False
    if wanted_document_type and _signal_document_type(signal) != wanted_document_type:
        return False
    return True


def _iter_recent_signals(
    db: Session,
    *,
    tenant_id,
    source_doc_type: str | None,
    document_type_hint: str | None = None,
    limit: int = 24,
) -> list[tuple[ImpRoutingSignal, ImpDocumento]]:
    rows = (
        db.query(ImpRoutingSignal, ImpDocumento)
        .join(ImpDocumento, ImpDocumento.id == ImpRoutingSignal.documento_id)
        .filter(ImpRoutingSignal.tenant_id == tenant_id)
        .order_by(ImpRoutingSignal.created_at.desc())
        .limit(max(limit * 4, 40))
        .all()
    )

    wanted = str(source_doc_type or "").strip().upper()
    selected: list[tuple[ImpRoutingSignal, ImpDocumento]] = []
    for signal, doc in rows:
        if not _signal_matches(
            signal,
            doc,
            source_doc_type=wanted,
            document_type_hint=document_type_hint,
        ):
            continue
        selected.append((signal, doc))
        if len(selected) >= limit:
            break
    return selected


def build_signal_learning_recipe_config(
    db: Session,
    *,
    tenant_id,
    source_doc_type: str | None,
    document_type_hint: str | None = None,
    base_recipe_config: dict[str, Any] | None = None,
    limit: int = 24,
) -> dict[str, Any]:
    base = dict(base_recipe_config or {})
    recent = _iter_recent_signals(
        db,
        tenant_id=tenant_id,
        source_doc_type=source_doc_type,
        document_type_hint=document_type_hint,
        limit=limit,
    )
    if not recent:
        return base

    route_counter: Counter[str] = Counter()
    corrected_fields: Counter[str] = Counter()
    confirmed_examples: dict[str, Counter[str]] = {}

    for index, (signal, doc) in enumerate(recent):
        recency_weight = max(0.45, 1.0 - (index * 0.04))
        signal_weight = _signal_quality_weight(signal) * recency_weight
        snapshot = signal.routing_snapshot if isinstance(signal.routing_snapshot, dict) else {}
        document_type = _normalize_text(snapshot.get("document_type"))
        if document_type:
            route_counter[document_type] += signal_weight

        for field in signal.changed_fields or []:
            key = _normalize_text(field)
            if not key or key.startswith("_") or key in _INTERNAL_KEYS:
                continue
            corrected_fields[key] += signal_weight

        confirmed = doc.datos_confirmados if isinstance(doc.datos_confirmados, dict) else {}
        for key, value in confirmed.items():
            field = _normalize_text(key)
            sample = _normalize_text(value)
            if not field or not sample or field.startswith("_") or field in _INTERNAL_KEYS:
                continue
            if not _is_scalar(value):
                continue
            confirmed_examples.setdefault(field, Counter())[sample] += signal_weight

    learned_field_descriptions = dict(base.get("field_descriptions") or {})
    for field, count in corrected_fields.most_common(5):
        if field in learned_field_descriptions:
            continue
        example_counter = confirmed_examples.get(field) or Counter()
        example_text = ""
        if example_counter:
            top_value, _ = example_counter.most_common(1)[0]
            example_text = f" Example recently confirmed: '{top_value}'."
        learned_field_descriptions[field] = (
            f"Field frequently corrected by users in similar documents (weight {count:.2f}). "
            "Read it carefully and leave null if absent."
            f"{example_text}"
        )

    guidance_lines: list[str] = []
    if route_counter:
        top_doc_type, top_count = route_counter.most_common(1)[0]
        guidance_lines.append(
            f"Recent high-quality similar documents were most often resolved as '{top_doc_type}' (score {top_count:.2f})."
        )
    if corrected_fields:
        guidance_lines.append(
            "Fields frequently corrected in similar documents: "
            + ", ".join(field for field, _count in corrected_fields.most_common(5))
            + "."
        )

    merged_prompt_user = str(base.get("prompt_user") or "").strip()
    if guidance_lines:
        learning_guidance = "Learning signals from user corrections:\n" + "\n".join(
            f"- {line}" for line in guidance_lines
        )
        merged_prompt_user = (
            f"{merged_prompt_user}\n\n{learning_guidance}".strip()
            if merged_prompt_user
            else learning_guidance
        )

    base["field_descriptions"] = learned_field_descriptions
    if merged_prompt_user:
        base["prompt_user"] = merged_prompt_user
    base["_signal_learning"] = {
        "signals_used": len(recent),
        "source_doc_type": str(source_doc_type or "").strip().upper() or None,
        "document_type_hint": str(document_type_hint or "").strip().lower() or None,
        "top_document_type": route_counter.most_common(1)[0][0] if route_counter else None,
        "top_corrected_fields": [field for field, _weight in corrected_fields.most_common(5)],
    }
    return base


def _filled_field_count(fields: dict[str, Any] | None) -> int:
    if not isinstance(fields, dict):
        return 0
    total = 0
    for key, value in fields.items():
        if str(key).startswith("_"):
            continue
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, (list, dict)) and not value:
            continue
        total += 1
    return total


def summarize_learning_rerun(
    *,
    baseline_doc_type: str,
    baseline_confidence: float,
    baseline_fields: dict[str, Any] | None,
    baseline_routing: dict[str, Any],
    rerun_doc_type: str,
    rerun_confidence: float,
    rerun_fields: dict[str, Any] | None,
    rerun_routing: dict[str, Any],
    signal_learning_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    baseline_missing = list(baseline_routing.get("missing_fields") or [])
    rerun_missing = list(rerun_routing.get("missing_fields") or [])
    confidence_delta = round(float(rerun_confidence or 0.0) - float(baseline_confidence or 0.0), 3)
    field_delta = _filled_field_count(rerun_fields) - _filled_field_count(baseline_fields)
    missing_delta = len(baseline_missing) - len(rerun_missing)
    destination_changed = (
        baseline_routing.get("suggested_destination") != rerun_routing.get("suggested_destination")
    )
    document_type_changed = baseline_routing.get("document_type") != rerun_routing.get("document_type")
    improved = (
        confidence_delta > 0
        or field_delta > 0
        or missing_delta > 0
        or (
            bool(rerun_routing.get("required_fields_ok"))
            and not bool(baseline_routing.get("required_fields_ok"))
        )
    )
    return {
        "used_learning_rerun": True,
        "improved": improved,
        "confidence_delta": confidence_delta,
        "field_count_delta": field_delta,
        "missing_fields_delta": missing_delta,
        "destination_changed": destination_changed,
        "document_type_changed": document_type_changed,
        "baseline": {
            "source_doc_type": baseline_doc_type,
            "confidence": round(float(baseline_confidence or 0.0), 3),
            "field_count": _filled_field_count(baseline_fields),
            "routing": baseline_routing,
        },
        "rerun": {
            "source_doc_type": rerun_doc_type,
            "confidence": round(float(rerun_confidence or 0.0), 3),
            "field_count": _filled_field_count(rerun_fields),
            "routing": rerun_routing,
        },
        "signal_learning": signal_learning_meta or {},
    }
