from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy.orm import Session

from app.models.importador import ImpDocumento, ImpRoutingSignal
from app.modules.importador.runtime_config import load_learning_config

from ._routing_signals import document_type as _signal_document_type
from ._routing_signals import event_weight as _event_weight
from ._routing_signals import is_scalar as _is_scalar
from ._routing_signals import normalize_text as _normalize_text
from ._routing_signals import source_doc_type as _signal_source_doc_type

_INTERNAL_KEYS = {
    "line_items",
    "rows",
    "_save",
}


def _signal_quality_weight(signal: ImpRoutingSignal, weights: dict | None = None) -> float:
    w = weights or {}
    snapshot = signal.routing_snapshot if isinstance(signal.routing_snapshot, dict) else {}
    weight = _event_weight(signal.event, w)
    if bool(snapshot.get("required_fields_ok")):
        weight += float(w.get("quality_bonus_required_fields_ok", 0.75))
    if not bool(snapshot.get("needs_human_review")):
        weight += float(w.get("quality_bonus_no_review_needed", 0.45))
    if str(signal.chosen_destination or "").strip():
        weight += float(w.get("quality_bonus_has_destination", 0.35))
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

    weights = load_learning_config(db)
    route_counter: Counter[str] = Counter()
    corrected_fields: Counter[str] = Counter()
    confirmed_examples: dict[str, Counter[str]] = {}

    for index, (signal, doc) in enumerate(recent):
        recency_weight = max(0.45, 1.0 - (index * 0.04))
        signal_weight = _signal_quality_weight(signal, weights) * recency_weight
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
    destination_changed = baseline_routing.get("suggested_destination") != rerun_routing.get(
        "suggested_destination"
    )
    document_type_changed = baseline_routing.get("document_type") != rerun_routing.get(
        "document_type"
    )
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


def _material_recipe_payload(config: dict[str, Any] | None) -> dict[str, Any]:
    payload = dict(config or {})
    payload.pop("_signal_learning", None)
    field_descriptions = payload.get("field_descriptions")
    if isinstance(field_descriptions, dict):
        payload["field_descriptions"] = {
            str(key).strip(): str(value).strip()
            for key, value in field_descriptions.items()
            if str(key).strip() and str(value).strip()
        }
    prompt_user = payload.get("prompt_user")
    if prompt_user is not None:
        payload["prompt_user"] = str(prompt_user).strip()
    return payload


def recipe_config_has_material_hints(
    base_recipe_config: dict[str, Any] | None,
    candidate_recipe_config: dict[str, Any] | None,
) -> bool:
    return _material_recipe_payload(base_recipe_config) != _material_recipe_payload(
        candidate_recipe_config
    )


def recipe_config_has_rerun_worthy_hints(
    base_recipe_config: dict[str, Any] | None,
    candidate_recipe_config: dict[str, Any] | None,
) -> bool:
    if not recipe_config_has_material_hints(base_recipe_config, candidate_recipe_config):
        return False

    base_payload = _material_recipe_payload(base_recipe_config)
    candidate_payload = _material_recipe_payload(candidate_recipe_config)

    base_field_descriptions = (
        base_payload.get("field_descriptions") if isinstance(base_payload, dict) else None
    )
    candidate_field_descriptions = (
        candidate_payload.get("field_descriptions") if isinstance(candidate_payload, dict) else None
    )
    if isinstance(candidate_field_descriptions, dict):
        baseline_fields = (
            base_field_descriptions if isinstance(base_field_descriptions, dict) else {}
        )
        for field_name, description in candidate_field_descriptions.items():
            if baseline_fields.get(field_name) != description:
                return True

    base_prompt_user = str(base_payload.get("prompt_user") or "").strip()
    candidate_prompt_user = str(candidate_payload.get("prompt_user") or "").strip()
    if candidate_prompt_user and candidate_prompt_user != base_prompt_user:
        return True

    base_model = str(base_payload.get("model") or "").strip()
    candidate_model = str(candidate_payload.get("model") or "").strip()
    if candidate_model and candidate_model != base_model:
        return True

    signal_meta = (
        candidate_recipe_config.get("_signal_learning")
        if isinstance(candidate_recipe_config, dict)
        else None
    )
    if isinstance(signal_meta, dict):
        if signal_meta.get("top_document_type"):
            return True
        if list(signal_meta.get("top_corrected_fields") or []):
            return True

    return False


def _field_needs_help(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict)):
        return not value
    return False


def should_run_learning_rerun(
    *,
    baseline_confidence: float,
    classification_threshold: float,
    baseline_fields: dict[str, Any] | None,
    baseline_routing: Any | None,
    base_recipe_config: dict[str, Any] | None,
    candidate_recipe_config: dict[str, Any] | None,
) -> bool:
    if not recipe_config_has_rerun_worthy_hints(base_recipe_config, candidate_recipe_config):
        return False

    routing = baseline_routing
    if routing is not None:
        missing_fields = list(getattr(routing, "missing_fields", None) or [])
        if missing_fields:
            return True
        if bool(getattr(routing, "needs_human_review", False)):
            return True
        if not bool(getattr(routing, "required_fields_ok", False)):
            return True

    candidate_fields = (
        candidate_recipe_config.get("field_descriptions")
        if isinstance(candidate_recipe_config, dict)
        else None
    )
    baseline = baseline_fields if isinstance(baseline_fields, dict) else {}
    if isinstance(candidate_fields, dict):
        for field_name in candidate_fields.keys():
            if _field_needs_help(baseline.get(str(field_name))):
                return True

    return float(baseline_confidence or 0.0) < float(classification_threshold or 0.0)
