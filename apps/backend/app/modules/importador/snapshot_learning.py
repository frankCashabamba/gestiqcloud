from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy.orm import Session

from . import crud, recipe_crud
from .constants import INTERNAL_STRUCTURAL_KEYS
from .runtime_config import load_snapshot_learning_config


def _max_learning_examples() -> int:
    return load_snapshot_learning_config().get("max_examples", 5)


def _normalize_scalar(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_examples(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized: list[str] = []
    for value in values:
        text = _normalize_scalar(value)
        if text and text not in normalized:
            normalized.append(text)
    return normalized[:_max_learning_examples()]


def _push_example(values: list[str], sample: str | None) -> list[str]:
    if not sample:
        return list(values)
    merged = [sample, *[value for value in values if value != sample]]
    return merged[:_max_learning_examples()]


def _coerce_counter(value: Any) -> int:
    try:
        count = int(value or 0)
    except (TypeError, ValueError):
        count = 0
    return max(0, count)


def build_learning_field_memory(
    datos_extraidos: dict[str, Any],
    datos_confirmados: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    updates: dict[str, dict[str, Any]] = {}
    for key, confirmed_val in datos_confirmados.items():
        if key in INTERNAL_STRUCTURAL_KEYS or str(key).startswith("_"):
            continue
        confirmed_text = _normalize_scalar(confirmed_val)
        if confirmed_text is None:
            continue

        original_val = datos_extraidos.get(key)
        original_text = _normalize_scalar(original_val)
        updates[str(key)] = {
            "confirmed_value": confirmed_text,
            "original_value": original_text,
            "was_corrected": confirmed_val != original_val,
        }
    return updates


def _render_learning_field_description(field: str, payload: dict[str, Any]) -> str:
    corrected_count = _coerce_counter(payload.get("corrected_count"))
    confirmed_count = _coerce_counter(payload.get("confirmed_count"))
    confirmed_examples = _normalize_examples(payload.get("confirmed_examples"))
    corrected_examples = _normalize_examples(payload.get("corrected_examples"))

    lines: list[str] = []
    if corrected_count > 0:
        lines.append(
            f"Users corrected '{field}' {corrected_count} time(s) in similar confirmed documents."
        )
    elif confirmed_count > 0:
        lines.append(f"'{field}' was confirmed {confirmed_count} time(s) in similar documents.")

    if corrected_examples:
        rendered = ", ".join(f"'{value}'" for value in corrected_examples[:3])
        lines.append(
            f"Recent confirmed values after correction: {rendered}. Use only if explicitly visible."
        )
    elif confirmed_examples:
        rendered = ", ".join(f"'{value}'" for value in confirmed_examples[:3])
        lines.append(f"Recent confirmed examples: {rendered}. Use only if explicitly visible.")

    last_original = _normalize_scalar(payload.get("last_original_value"))
    last_confirmed = _normalize_scalar(payload.get("last_confirmed_value"))
    if last_original and last_confirmed and last_original != last_confirmed:
        lines.append(f"Latest correction replaced '{last_original}' with '{last_confirmed}'.")

    return " ".join(lines).strip()


def _build_learning_prompt(memory: dict[str, dict[str, Any]]) -> str | None:
    ranked: list[tuple[str, dict[str, Any]]] = []
    for field, payload in memory.items():
        corrected_count = _coerce_counter(payload.get("corrected_count"))
        confirmed_count = _coerce_counter(payload.get("confirmed_count"))
        if corrected_count <= 0 and confirmed_count <= 0:
            continue
        ranked.append((field, payload))

    if not ranked:
        return None

    ranked.sort(
        key=lambda item: (
            -_coerce_counter(item[1].get("corrected_count")),
            -_coerce_counter(item[1].get("confirmed_count")),
            item[0],
        )
    )

    lines = ["Learning from confirmed similar documents:"]
    for field, payload in ranked[:5]:
        corrected_count = _coerce_counter(payload.get("corrected_count"))
        confirmed_examples = _normalize_examples(payload.get("confirmed_examples"))
        if corrected_count > 0:
            line = f"- Review '{field}' carefully; users corrected it {corrected_count} time(s)."
        else:
            line = f"- '{field}' was confirmed repeatedly in similar documents."
        if confirmed_examples:
            line += (
                " Recent examples: "
                + ", ".join(f"'{value}'" for value in confirmed_examples[:2])
                + "."
            )
        lines.append(line)
    lines.append("- Reuse examples only when the value is explicitly visible in the document.")
    return "\n".join(lines)


def build_snapshot_review_hints(
    snapshot,
    *,
    missing_fields: list[str] | None = None,
    canonical_fields: dict[str, dict[str, Any]] | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    if snapshot is None or not isinstance(getattr(snapshot, "content_json", None), dict):
        return []

    content = dict(snapshot.content_json or {})
    raw_memory = content.get("field_learning_memory")
    if not isinstance(raw_memory, dict):
        return []

    missing = {str(field).strip() for field in (missing_fields or []) if str(field).strip()}
    canonical_meta = canonical_fields or {}
    ranked: list[tuple[tuple[int, int, int, str], dict[str, Any]]] = []

    for raw_field, raw_payload in raw_memory.items():
        field = _normalize_scalar(raw_field)
        if not field or not isinstance(raw_payload, dict):
            continue
        corrected_count = _coerce_counter(raw_payload.get("corrected_count"))
        confirmed_count = _coerce_counter(raw_payload.get("confirmed_count"))
        if corrected_count <= 0 and confirmed_count <= 0:
            continue

        field_type = str((canonical_meta.get(field) or {}).get("type") or "text").strip().lower()
        confirmed_examples = _normalize_examples(raw_payload.get("confirmed_examples"))
        hint = {
            "field": field,
            "field_type": field_type or "text",
            "priority": 1000,
            "is_missing": field in missing,
            "corrected_count": corrected_count,
            "confirmed_count": confirmed_count,
            "confirmed_examples": confirmed_examples[:3],
            "last_confirmed_value": _normalize_scalar(raw_payload.get("last_confirmed_value")),
            "reason": _render_learning_field_description(field, raw_payload),
        }
        priority_key = (
            0 if hint["is_missing"] else 1,
            -corrected_count,
            -confirmed_count,
            field,
        )
        ranked.append((priority_key, hint))

    ranked.sort(key=lambda item: item[0])
    hints = [hint for _key, hint in ranked[: max(1, limit)]]
    for index, hint in enumerate(hints, start=1):
        hint["priority"] = index
    return hints


def build_learning_field_descriptions(
    datos_extraidos: dict[str, Any],
    datos_confirmados: dict[str, Any],
) -> dict[str, str]:
    memory = build_learning_field_memory(datos_extraidos, datos_confirmados)
    descriptions: dict[str, str] = {}
    for field, payload in memory.items():
        descriptions[field] = _render_learning_field_description(
            field,
            {
                "confirmed_count": 1,
                "corrected_count": 1 if payload.get("was_corrected") else 0,
                "confirmed_examples": [payload.get("confirmed_value")],
                "corrected_examples": (
                    [payload.get("confirmed_value")] if payload.get("was_corrected") else []
                ),
                "last_original_value": payload.get("original_value"),
                "last_confirmed_value": payload.get("confirmed_value"),
            },
        )
    return descriptions


def apply_learning_to_snapshot(
    db: Session,
    *,
    snapshot,
    hints: dict[str, str],
    memory_updates: dict[str, dict[str, Any]] | None = None,
) -> bool:
    if snapshot is None:
        return False

    content = dict(snapshot.content_json or {})
    learned_field_descriptions = dict(content.get("learned_field_descriptions") or {})
    field_memory_raw = content.get("field_learning_memory")
    field_memory: dict[str, dict[str, Any]] = {}
    if isinstance(field_memory_raw, dict):
        for key, payload in field_memory_raw.items():
            name = _normalize_scalar(key)
            if not name or not isinstance(payload, dict):
                continue
            field_memory[name] = dict(payload)

    changed = False
    for key, payload in (memory_updates or {}).items():
        name = _normalize_scalar(key)
        if not name or not isinstance(payload, dict):
            continue
        confirmed_value = _normalize_scalar(payload.get("confirmed_value"))
        if not confirmed_value:
            continue
        current = dict(field_memory.get(name) or {})
        next_payload = {
            "confirmed_count": _coerce_counter(current.get("confirmed_count")) + 1,
            "corrected_count": (
                _coerce_counter(current.get("corrected_count"))
                + (1 if payload.get("was_corrected") else 0)
            ),
            "confirmed_examples": _push_example(
                _normalize_examples(current.get("confirmed_examples")),
                confirmed_value,
            ),
            "corrected_examples": (
                _push_example(
                    _normalize_examples(current.get("corrected_examples")),
                    confirmed_value,
                )
                if payload.get("was_corrected")
                else _normalize_examples(current.get("corrected_examples"))
            ),
            "last_original_value": payload.get("original_value"),
            "last_confirmed_value": confirmed_value,
        }
        if field_memory.get(name) != next_payload:
            field_memory[name] = next_payload
            changed = True

    for key, value in hints.items():
        name = _normalize_scalar(key)
        text = _normalize_scalar(value)
        if not name or not text:
            continue
        if learned_field_descriptions.get(name) == text and name in field_memory:
            continue
        learned_field_descriptions[name] = text
        changed = True

    for key, payload in field_memory.items():
        rendered = _render_learning_field_description(key, payload)
        if rendered and learned_field_descriptions.get(key) != rendered:
            learned_field_descriptions[key] = rendered
            changed = True

    learning_prompt_user = _build_learning_prompt(field_memory)
    if not changed and content.get("learning_prompt_user") == learning_prompt_user:
        return False

    learning_version = 0
    try:
        learning_version = int(content.get("learning_version") or 0)
    except (TypeError, ValueError):
        learning_version = 0

    content["learned_field_descriptions"] = learned_field_descriptions
    content["field_learning_memory"] = field_memory
    content["learning_prompt_user"] = learning_prompt_user
    content["learning_version"] = learning_version + 1
    content["learning_updated_at"] = datetime.datetime.now(datetime.UTC).isoformat()
    snapshot.content_json = content
    db.flush()
    return True


def learn_from_confirmed_payload(
    db: Session,
    doc,
    datos_confirmados: dict[str, Any],
    user_id: str,
) -> bool:
    if not doc.recipe_snapshot_id:
        return False

    datos_extraidos = doc.datos_extraidos or {}
    if not isinstance(datos_extraidos, dict) or not isinstance(datos_confirmados, dict):
        return False

    snapshot = recipe_crud.get_snapshot(db, doc.recipe_snapshot_id)
    if snapshot is None:
        return False

    hints = build_learning_field_descriptions(datos_extraidos, datos_confirmados)
    memory_updates = build_learning_field_memory(datos_extraidos, datos_confirmados)
    changed = apply_learning_to_snapshot(
        db,
        snapshot=snapshot,
        hints=hints,
        memory_updates=memory_updates,
    )
    if changed:
        crud.add_log(
            db,
            doc.id,
            "LEARN",
            user_id,
            {"corrections": hints, "snapshot_id": str(snapshot.id)},
        )
    return changed


def bootstrap_learning_from_existing_document(
    db: Session,
    doc,
    user_id: str = "system",
) -> bool:
    confirmed = doc.datos_confirmados or {}
    if not isinstance(confirmed, dict) or not confirmed:
        return False
    return learn_from_confirmed_payload(db, doc, confirmed, user_id)
