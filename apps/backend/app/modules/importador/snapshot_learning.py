from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy.orm import Session

from . import crud, recipe_crud

_SKIP_KEYS = {
    "filas",
    "total_filas",
    "columnas",
    "columnas_norm",
    "hojas",
    "sheet_usada",
    "metadata",
    "filas_por_hoja",
    "filas_por_hoja_count",
}


def _is_scalar_learning_value(value: Any) -> bool:
    return value is not None and not isinstance(value, (dict, list, tuple, set, bool))


def _normalize_scalar(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def build_learning_field_descriptions(
    datos_extraidos: dict[str, Any],
    datos_confirmados: dict[str, Any],
) -> dict[str, str]:
    hints: dict[str, str] = {}
    for key, confirmed_val in datos_confirmados.items():
        if key in _SKIP_KEYS or str(key).startswith("_"):
            continue
        original_val = datos_extraidos.get(key)
        confirmed_text = _normalize_scalar(confirmed_val)
        original_text = _normalize_scalar(original_val)
        if confirmed_text is None:
            continue

        if confirmed_val != original_val:
            hints[str(key)] = (
                f"User corrected '{key}': expected '{confirmed_text}' (was '{original_text}')"
            )
            continue

        if _is_scalar_learning_value(confirmed_val):
            hints[str(key)] = (
                f"Confirmed example for '{key}': '{confirmed_text}'. "
                "Reuse this as a learned hint for similar documents."
            )
    return hints


def apply_learning_to_snapshot(
    db: Session,
    *,
    snapshot,
    hints: dict[str, str],
) -> bool:
    if snapshot is None or not hints:
        return False

    content = dict(snapshot.content_json or {})
    field_descriptions = dict(content.get("field_descriptions") or {})
    changed = False
    for key, value in hints.items():
        if field_descriptions.get(key) == value:
            continue
        field_descriptions[key] = value
        changed = True

    if not changed:
        return False

    learning_version = 0
    try:
        learning_version = int(content.get("learning_version") or 0)
    except (TypeError, ValueError):
        learning_version = 0

    content["field_descriptions"] = field_descriptions
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
    changed = apply_learning_to_snapshot(db, snapshot=snapshot, hints=hints)
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
    confirmed = doc.datos_confirmados or doc.datos_extraidos or {}
    if not isinstance(confirmed, dict) or not confirmed:
        return False
    return learn_from_confirmed_payload(db, doc, confirmed, user_id)
