"""Auto-generation and reuse of recipes based on detected headers/fingerprints."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import String, cast, select
from sqlalchemy.orm import Session

from app.models.importador import IcuRecipeSnapshot

from . import recipe_crud


def _fingerprint_hash(obj: dict) -> str:
    payload = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_fingerprint(sheet_profiles: dict) -> tuple[dict, str]:
    """Build a tenant-agnostic fingerprint from sheet_profiles (Excel/CSV)."""
    normalized = {}
    for sheet, prof in (sheet_profiles or {}).items():
        headers = prof.get("headers_norm") or prof.get("headers") or []
        col_types = prof.get("column_profiles", {})
        normalized[sheet] = {
            "headers": headers,
            "column_types": {k: v.get("type") for k, v in col_types.items()} if col_types else {},
        }
    fp = {"kind": "excel", "sheets": normalized}
    return fp, _fingerprint_hash(fp)


def build_text_fingerprint(
    tipo_doc: str, datos_extraidos: dict | None, format_hint: str
) -> tuple[dict, str]:
    """Build a fingerprint for PDF/XML/image/TXT based on document type + field structure."""
    campos = sorted(
        k
        for k in (datos_extraidos or {}).keys()
        if not k.startswith("_") and k not in ("filas", "total_filas")
    )
    fp = {"kind": "text", "tipo_documento": tipo_doc, "campos": campos, "formato": format_hint}
    return fp, _fingerprint_hash(fp)


def find_snapshot_by_hash(db: Session, tenant_id: UUID, fp_hash: str):
    Snap = IcuRecipeSnapshot
    stmt = (
        select(Snap)
        .where(
            Snap.tenant_id == tenant_id,
            cast(Snap.content_json["fingerprint_hash"], String) == fp_hash,
        )
        .order_by(Snap.created_at.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()


def _auto_prompts_excel(headers_flat: list[str]) -> dict:
    prompt_system = (
        "Eres un extractor contable. Usa SOLO las columnas listadas.\n"
        f"Columnas detectadas: {headers_flat}\n"
        "- Si un campo no está en las columnas, devuélvelo como null.\n"
        "- Fechas en YYYY-MM-DD. Montos en número con punto decimal.\n"
        "- No inventes valores."
    )
    return {"prompt_system": prompt_system, "prompt_user": None, "model": None}


def _auto_prompts_text(tipo_doc: str, campos: list[str]) -> dict:
    prompt_system = (
        f"Eres un extractor contable especializado en documentos de tipo {tipo_doc}.\n"
        f"Campos típicos detectados en este formato: {campos}\n"
        "- Fechas en YYYY-MM-DD. Montos en número con punto decimal.\n"
        "- Si un campo no está presente, devuélvelo como null.\n"
        "- No inventes valores ni asumas datos que no estén en el documento."
    )
    return {"prompt_system": prompt_system, "prompt_user": None, "model": None}


def _create_recipe_and_snapshot(
    db: Session,
    tenant_id: UUID,
    name: str,
    description: str,
    fp: dict,
    fp_hash: str,
    prompts: dict,
    extra_content: dict,
    created_by: str | None,
) -> tuple[str, IcuRecipeSnapshot]:
    recipe = recipe_crud.create_recipe(
        db,
        {
            "tenant_id": tenant_id,
            "name": name,
            "description": description,
            "is_public": False,
            "created_by": created_by,
        },
    )
    draft = recipe_crud.create_draft(
        db,
        {
            "tenant_id": tenant_id,
            "recipe_id": recipe.id,
            "prompt_system": prompts["prompt_system"],
            "prompt_user": prompts["prompt_user"],
            "model_config": {"model": prompts["model"]} if prompts.get("model") else None,
            "updated_by": created_by,
        },
    )
    snapshot = recipe_crud.create_snapshot(
        db,
        {
            "tenant_id": tenant_id,
            "recipe_id": recipe.id,
            "draft_id": draft.id,
            "version_tag": "auto-1",
            "content_json": {
                "fingerprint_hash": fp_hash,
                "fingerprint": fp,
                "prompt_system": prompts["prompt_system"],
                "prompt_user": prompts["prompt_user"],
                "model": prompts["model"],
                **extra_content,
            },
            "created_by": created_by,
        },
    )
    return recipe.name, snapshot


def _flatten_headers(sheet_profiles: dict) -> list[str]:
    headers = []
    for prof in (sheet_profiles or {}).values():
        headers.extend(prof.get("headers", []) or prof.get("headers_norm", []))
    seen: set[str] = set()
    uniq = []
    for h in headers:
        if h not in seen:
            seen.add(h)
            uniq.append(h)
    return uniq


def _learning_min_confidence() -> float:
    raw = (os.getenv("IMPORTADOR_CACHE_MIN_CONFIDENCE") or "").strip()
    if not raw:
        return 0.6
    try:
        return max(0.0, min(1.0, float(raw)))
    except ValueError:
        return 0.6


def get_snapshot_learning(
    snapshot: IcuRecipeSnapshot | None,
    *,
    structured_only: bool = False,
) -> dict | None:
    """Return cached analysis learned for this fingerprint snapshot, if any."""
    if snapshot is None or not isinstance(snapshot.content_json, dict):
        return None

    learned = snapshot.content_json.get("learned_analysis")
    if not isinstance(learned, dict):
        return None

    cache_key = "structured" if structured_only else "default"
    cached = learned.get(cache_key)
    if not isinstance(cached, dict):
        return None
    try:
        confidence = float(cached.get("confidence") or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0
    return cached if confidence >= _learning_min_confidence() else None


def remember_snapshot_learning(
    db: Session,
    snapshot: IcuRecipeSnapshot | None,
    analysis: dict,
    *,
    structured_only: bool = False,
) -> None:
    """Persist a successful analysis as reusable knowledge for this fingerprint."""
    if snapshot is None:
        return

    doc_type = str(analysis.get("doc_type") or "").strip().upper()
    if not doc_type or doc_type == "OTHER":
        return

    try:
        confidence = float(analysis.get("confidence") or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0
    if confidence < _learning_min_confidence():
        return

    content = dict(snapshot.content_json or {})
    learned = dict(content.get("learned_analysis") or {})
    cache_key = "structured" if structured_only else "default"
    learned[cache_key] = {
        "doc_type": doc_type,
        "confidence": confidence,
        "reasoning": str(analysis.get("reasoning") or "").strip(),
        "updated_at": datetime.now(UTC).isoformat(),
    }
    content["learned_analysis"] = learned
    snapshot.content_json = content
    db.flush()


def resolve_auto_recipe(
    db: Session,
    tenant_id: UUID,
    sheet_profiles: dict,
    created_by: str | None = None,
    force_new: bool = False,
) -> tuple[dict, UUID | None, str, bool, str | None]:
    """Excel/CSV: return (recipe_config, snapshot_id, mode, created, recipe_name).

    force_new=True fuerza crear un snapshot nuevo ignorando coincidencias previas
    (útil para reimportar sin arrastrar recetas anteriores).
    """
    if not sheet_profiles:
        return {}, None, "zero_shot", False, None
    fp, fp_hash = build_fingerprint(sheet_profiles)
    snap = None if force_new else find_snapshot_by_hash(db, tenant_id, fp_hash)
    created = False
    recipe_name: str | None = None
    if not snap:
        prompts = _auto_prompts_excel(_flatten_headers(sheet_profiles))
        name = f"auto-excel-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
        recipe_name, snap = _create_recipe_and_snapshot(
            db,
            tenant_id,
            name,
            "Generada automáticamente por fingerprint de cabeceras Excel",
            fp,
            fp_hash,
            prompts,
            {"sheet_profiles": sheet_profiles},
            created_by,
        )
        created = True
        db.commit()
    recipe_config = {
        "prompt_system": snap.content_json.get("prompt_system"),
        "prompt_user": snap.content_json.get("prompt_user"),
        "model": (
            snap.content_json.get("model")
            or (snap.content_json.get("model_config") or {}).get("model")
        ),
    }
    return recipe_config, snap.id, "auto_fingerprint", created, recipe_name


def resolve_auto_recipe_from_text(
    db: Session,
    tenant_id: UUID,
    tipo_doc: str,
    datos_extraidos: dict | None,
    format_hint: str,
    created_by: str | None = None,
    force_new: bool = False,
) -> tuple[dict, UUID | None, str, bool, str | None]:
    """PDF/XML/imagen/TXT: fingerprint post-extraccion. Crea snapshot si no existe.

    force_new=True fuerza crear snapshot nuevo aunque ya exista uno para el mismo fingerprint.
    Returns (recipe_config, snapshot_id, mode, was_created, recipe_name).
    La primera subida es zero-shot; el snapshot queda guardado para futuras similares.
    """
    campos = [
        k
        for k in (datos_extraidos or {}).keys()
        if not k.startswith("_") and k not in ("filas", "total_filas")
    ]
    if not campos:
        return {}, None, "zero_shot", False, None

    fp, fp_hash = build_text_fingerprint(tipo_doc, datos_extraidos, format_hint)
    snap = None if force_new else find_snapshot_by_hash(db, tenant_id, fp_hash)
    was_created = False
    recipe_name: str | None = None

    if not snap:
        prompts = _auto_prompts_text(tipo_doc, sorted(campos))
        name = f"auto-{tipo_doc.lower()}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
        recipe_name, snap = _create_recipe_and_snapshot(
            db,
            tenant_id,
            name,
            f"Generada automaticamente para {tipo_doc} ({format_hint})",
            fp,
            fp_hash,
            prompts,
            {},
            created_by,
        )
        was_created = True

    recipe_config = {
        "prompt_system": snap.content_json.get("prompt_system"),
        "prompt_user": snap.content_json.get("prompt_user"),
        "model": snap.content_json.get("model"),
    }
    return recipe_config, snap.id, "auto_text_fingerprint", was_created, recipe_name
