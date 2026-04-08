"""Auto-generation and reuse of recipes based on detected headers/fingerprints."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import array as pg_array
from sqlalchemy.orm import Session

from app.models.importador import IcuRecipeSnapshot

from . import recipe_crud
from .runtime_config import load_fuzzy_reuse_config, load_learning_control


def _fingerprint_hash(obj: dict) -> str:
    payload = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _fingerprint_signature(obj: dict | None) -> str | None:
    if not isinstance(obj, dict):
        return None
    return json.dumps(obj, sort_keys=True, default=str, separators=(",", ":"))


def _ensure_snapshot_fingerprint_metadata(
    db: Session,
    snapshot: IcuRecipeSnapshot | None,
    *,
    fingerprint: dict | None = None,
    fp_hash: str | None = None,
) -> IcuRecipeSnapshot | None:
    if snapshot is None:
        return None

    content = snapshot.content_json if isinstance(snapshot.content_json, dict) else {}
    stored_fingerprint = (
        fingerprint if isinstance(fingerprint, dict) else content.get("fingerprint")
    )
    normalized_fingerprint = _normalize_fingerprint_payload(stored_fingerprint)
    changed = False

    signature = _fingerprint_signature(normalized_fingerprint)
    if signature and str(content.get("fingerprint_signature") or "").strip() != signature:
        content = dict(content)
        content["fingerprint_signature"] = signature
        changed = True

    fingerprint_kind = (
        str((normalized_fingerprint or {}).get("kind") or "").strip().lower()
        if isinstance(normalized_fingerprint, dict)
        else ""
    )
    if (
        fingerprint_kind
        and str(content.get("fingerprint_kind") or "").strip().lower() != fingerprint_kind
    ):
        if not changed:
            content = dict(content)
        content["fingerprint_kind"] = fingerprint_kind
        changed = True

    headers_flat = _excel_headers_flat_from_fingerprint(normalized_fingerprint)
    if headers_flat and content.get("fingerprint_headers_flat") != headers_flat:
        if not changed:
            content = dict(content)
        content["fingerprint_headers_flat"] = headers_flat
        changed = True

    stored_hash = str(content.get("fingerprint_hash") or "").strip()
    if fp_hash and not stored_hash:
        if not changed:
            content = dict(content)
        content["fingerprint_hash"] = fp_hash
        changed = True

    if changed:
        snapshot.content_json = content
        db.flush()
    return snapshot


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
    del tipo_doc
    campos = sorted(
        k
        for k in (datos_extraidos or {}).keys()
        if not k.startswith("_") and k not in ("filas", "total_filas")
    )
    fp = {
        "kind": "text",
        "campos": campos,
        "formato": format_hint,
    }
    return fp, _fingerprint_hash(fp)


def _excel_header_overlap(target_sheets: dict, stored_sheets: dict) -> float:
    """Jaccard similarity entre el conjunto de headers de dos fingerprints Excel."""
    target_headers: set[str] = set()
    stored_headers: set[str] = set()
    for prof in target_sheets.values():
        target_headers.update(str(h).strip().lower() for h in (prof.get("headers") or []) if h)
    for prof in stored_sheets.values():
        stored_headers.update(str(h).strip().lower() for h in (prof.get("headers") or []) if h)
    if not target_headers or not stored_headers:
        return 0.0
    intersection = len(target_headers & stored_headers)
    union = len(target_headers | stored_headers)
    return intersection / union if union else 0.0


def _excel_headers_flat_from_fingerprint(fingerprint: dict | None) -> list[str]:
    if (
        not isinstance(fingerprint, dict)
        or str(fingerprint.get("kind") or "").strip().lower() != "excel"
    ):
        return []
    sheets = fingerprint.get("sheets") or {}
    headers: set[str] = set()
    for prof in sheets.values():
        if not isinstance(prof, dict):
            continue
        for header in prof.get("headers") or []:
            normalized = str(header or "").strip().lower()
            if normalized:
                headers.add(normalized)
    return sorted(headers)


def find_similar_excel_snapshot(
    db: Session,
    tenant_id: UUID,
    fingerprint: dict,
    *,
    min_overlap: float | None = None,
) -> IcuRecipeSnapshot | None:
    """Busca el snapshot Excel más similar por overlap de headers (Jaccard >= min_overlap).

    Solo aplica a fingerprints de tipo 'excel'. Retorna el mejor candidato o None.
    Limita la búsqueda a los 100 snapshots más recientes del tenant para rendimiento.
    """
    if min_overlap is None:
        min_overlap = load_fuzzy_reuse_config(db).get("excel_min_overlap", 0.80)
    if not isinstance(fingerprint, dict) or fingerprint.get("kind") != "excel":
        return None
    target_sheets = fingerprint.get("sheets") or {}
    if not target_sheets:
        return None
    target_headers_flat = _excel_headers_flat_from_fingerprint(fingerprint)

    stmt = select(IcuRecipeSnapshot).where(
        IcuRecipeSnapshot.tenant_id == tenant_id,
        IcuRecipeSnapshot.content_json.op("?")("fingerprint_kind"),
        func.jsonb_extract_path_text(IcuRecipeSnapshot.content_json, "fingerprint_kind") == "excel",
    )
    if target_headers_flat:
        stmt = stmt.where(
            IcuRecipeSnapshot.content_json.op("?")("fingerprint_headers_flat"),
            IcuRecipeSnapshot.content_json["fingerprint_headers_flat"].op("?|")(
                pg_array(target_headers_flat)
            ),
        )
    stmt = stmt.order_by(IcuRecipeSnapshot.created_at.desc()).limit(100)
    best_snap: IcuRecipeSnapshot | None = None
    best_overlap = 0.0
    candidates = list(db.scalars(stmt))
    if not candidates:
        fallback_stmt = (
            select(IcuRecipeSnapshot)
            .where(IcuRecipeSnapshot.tenant_id == tenant_id)
            .order_by(IcuRecipeSnapshot.created_at.desc())
            .limit(100)
        )
        candidates = list(db.scalars(fallback_stmt))
    for snap in candidates:
        content = snap.content_json if isinstance(snap.content_json, dict) else {}
        stored_fp = content.get("fingerprint")
        if not isinstance(stored_fp, dict) or stored_fp.get("kind") != "excel":
            continue
        overlap = _excel_header_overlap(target_sheets, stored_fp.get("sheets") or {})
        if overlap >= min_overlap and overlap > best_overlap:
            best_overlap = overlap
            best_snap = snap
    return _ensure_snapshot_fingerprint_metadata(db, best_snap, fingerprint=fingerprint)


def _normalize_fingerprint_payload(fingerprint: dict | None) -> dict | None:
    if not isinstance(fingerprint, dict):
        return None

    kind = str(fingerprint.get("kind") or "").strip().lower()
    if kind != "text":
        return fingerprint

    campos = sorted(
        str(key)
        for key in (fingerprint.get("campos") or [])
        if str(key) and not str(key).startswith("_")
    )

    return {
        "kind": "text",
        "campos": campos,
        "formato": str(fingerprint.get("formato") or "").strip(),
    }


def find_snapshot_by_hash(
    db: Session,
    tenant_id: UUID,
    fp_hash: str,
    *,
    fingerprint: dict | None = None,
):
    Snap = IcuRecipeSnapshot
    stmt = (
        select(Snap)
        .where(
            Snap.tenant_id == tenant_id,
            Snap.content_json.op("?")("fingerprint_hash"),
            func.jsonb_extract_path_text(Snap.content_json, "fingerprint_hash") == fp_hash,
        )
        .order_by(Snap.created_at.desc())
        .limit(1)
    )
    found = db.scalars(stmt).first()
    if found:
        return _ensure_snapshot_fingerprint_metadata(
            db,
            found,
            fingerprint=fingerprint,
            fp_hash=fp_hash,
        )

    normalized_target = _normalize_fingerprint_payload(fingerprint)
    signature = _fingerprint_signature(normalized_target)
    if signature:
        signature_stmt = (
            select(Snap)
            .where(
                Snap.tenant_id == tenant_id,
                Snap.content_json.op("?")("fingerprint_signature"),
                func.jsonb_extract_path_text(Snap.content_json, "fingerprint_signature")
                == signature,
            )
            .order_by(Snap.created_at.desc())
            .limit(1)
        )
        by_signature = db.scalars(signature_stmt).first()
        if by_signature:
            return _ensure_snapshot_fingerprint_metadata(
                db,
                by_signature,
                fingerprint=normalized_target,
                fp_hash=fp_hash,
            )

    fallback_stmt = (
        select(Snap).where(Snap.tenant_id == tenant_id).order_by(Snap.created_at.desc()).limit(200)
    )
    for snap in db.scalars(fallback_stmt):
        content = snap.content_json if isinstance(snap.content_json, dict) else {}
        if str(content.get("fingerprint_hash") or "").strip() == fp_hash:
            return _ensure_snapshot_fingerprint_metadata(
                db,
                snap,
                fingerprint=fingerprint,
                fp_hash=fp_hash,
            )
        if normalized_target is not None:
            stored_fingerprint = _normalize_fingerprint_payload(content.get("fingerprint"))
            if stored_fingerprint == normalized_target:
                return _ensure_snapshot_fingerprint_metadata(
                    db,
                    snap,
                    fingerprint=normalized_target,
                    fp_hash=fp_hash,
                )
    return None


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
    headers_flat = _excel_headers_flat_from_fingerprint(fp)
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
                "fingerprint_signature": _fingerprint_signature(fp),
                "fingerprint_kind": str(fp.get("kind") or "").strip().lower() or None,
                **({"fingerprint_headers_flat": headers_flat} if headers_flat else {}),
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
    return load_fuzzy_reuse_config().get("learning_min_confidence", 0.6)


def _coerce_learning_version(value: object) -> int:
    try:
        version = int(value or 0)
    except (TypeError, ValueError):
        version = 0
    return max(0, version)


def _merge_prompt_user(base_prompt: object, learning_prompt: object) -> str | None:
    base = str(base_prompt or "").strip()
    learning = str(learning_prompt or "").strip()
    if base and learning:
        return f"{base}\n\n{learning}"
    if base:
        return base
    return learning or None


def _snapshot_recipe_config(snapshot: IcuRecipeSnapshot) -> dict:
    content = snapshot.content_json if isinstance(snapshot.content_json, dict) else {}
    base_descriptions = dict(content.get("field_descriptions") or {})
    learned_descriptions = dict(content.get("learned_field_descriptions") or {})
    merged_descriptions = {**base_descriptions, **learned_descriptions}
    return {
        "prompt_system": content.get("prompt_system"),
        "prompt_user": _merge_prompt_user(
            content.get("prompt_user"),
            content.get("learning_prompt_user"),
        ),
        "model": content.get("model") or (content.get("model_config") or {}).get("model"),
        "field_descriptions": merged_descriptions or None,
    }


def get_snapshot_learning_version(snapshot: IcuRecipeSnapshot | None) -> int:
    if snapshot is None or not isinstance(snapshot.content_json, dict):
        return 0
    return _coerce_learning_version(snapshot.content_json.get("learning_version"))


def get_document_applied_learning_version(raw_ai_json: dict | None) -> int:
    if not isinstance(raw_ai_json, dict):
        return 0

    run = raw_ai_json.get("run")
    if isinstance(run, dict):
        direct = run.get("learning_version_applied")
        if direct is not None:
            return _coerce_learning_version(direct)
        recipe_resolution = run.get("recipe_resolution")
        if isinstance(recipe_resolution, dict):
            return _coerce_learning_version(recipe_resolution.get("learning_version_applied"))
    return 0


def should_reprocess_existing_document(db: Session, doc) -> bool:
    """Política de reuso vs reproceso por learning_version.

    Los cuatro casos posibles cuando se re-sube un documento ya existente:

    1. RECREACIÓN (fingerprint cambió):
       El doc entrante tendrá un hash_sha256 distinto → crud.find_existing_documento
       no lo empareja → se crea un documento nuevo y se procesa desde cero.
       Esta función nunca es invocada en ese caso.

    2. REUSO EXACTO (mismo fingerprint, mismo learning_version):
       El snapshot existe pero su learning_version == la versión ya aplicada al
       documento (applied_version == current_version). Retorna False → skip.

    3. SKIP (mismo fingerprint, snapshot sin aprendizaje):
       El snapshot existe pero nunca acumuló aprendizaje (learning_version == 0,
       es decir, ningún análisis confirmado fue almacenado todavía).
       Retorna False → no tiene sentido re-ejecutar con hints vacíos.

    4. REPROCESO POR LEARNING (mismo fingerprint, snapshot aprendió algo nuevo):
       El snapshot tiene learning_version > 0 Y applied_version < current_version,
       lo que significa que el doc fue procesado antes de que el snapshot acumulara
       nuevos hints aprendidos. Retorna True → re-ejecutar AI con los hints actuales.
       Condicionado además a que rerun_enabled=true en learning_control (runtime_seed).
    """
    # El doc debe tener un snapshot asociado (sólo documentos que pasaron por el
    # pipeline de recetas tendrán recipe_snapshot_id).
    snapshot_id = getattr(doc, "recipe_snapshot_id", None)
    if not snapshot_id:
        return False

    snapshot = db.get(IcuRecipeSnapshot, snapshot_id)
    if snapshot is None:
        return False

    # Caso 3 — SKIP: snapshot sin aprendizaje acumulado.
    current_version = get_snapshot_learning_version(snapshot)
    if current_version <= 0:
        return False

    # Caso 2 — REUSO EXACTO: ya se procesó con la versión de aprendizaje actual.
    applied_version = get_document_applied_learning_version(getattr(doc, "raw_ai_json", None))
    if applied_version >= current_version:
        return False

    # Caso 4 — REPROCESO POR LEARNING: nueva versión disponible.
    # Verificar las puertas de control del operador en learning_control.
    learning_ctrl = load_learning_control(db)

    # Puerta global: rerun_enabled=false bloquea todo reproceso por aprendizaje.
    if not learning_ctrl.get("rerun_enabled", True):
        return False

    # skip_reprocess_confirmed=true protege documentos ya aprobados (CONFIRMED)
    # de ser re-encolados automáticamente; solo los REVIEW quedan elegibles.
    if learning_ctrl.get("skip_reprocess_confirmed", False):
        estado = str(getattr(doc, "estado", "") or "").upper()
        if estado == "CONFIRMED":
            return False

    return True


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
    candidate = {
        "doc_type": doc_type,
        "confidence": confidence,
        "reasoning": str(analysis.get("reasoning") or "").strip(),
        "updated_at": datetime.now(UTC).isoformat(),
    }
    previous = learned.get(cache_key)
    previous_cmp = (
        {
            "doc_type": previous.get("doc_type"),
            "confidence": previous.get("confidence"),
            "reasoning": previous.get("reasoning"),
        }
        if isinstance(previous, dict)
        else None
    )
    candidate_cmp = {
        "doc_type": candidate["doc_type"],
        "confidence": candidate["confidence"],
        "reasoning": candidate["reasoning"],
    }
    if previous_cmp == candidate_cmp:
        return

    learned[cache_key] = candidate
    content["learned_analysis"] = learned
    content["learning_version"] = _coerce_learning_version(content.get("learning_version")) + 1
    content["learning_updated_at"] = candidate["updated_at"]
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
    snap = None if force_new else find_snapshot_by_hash(db, tenant_id, fp_hash, fingerprint=fp)
    created = False
    recipe_name: str | None = None
    if not snap:
        prompts = _auto_prompts_excel(_flatten_headers(sheet_profiles))
        extra_content: dict = {"sheet_profiles": sheet_profiles}
        # Fuzzy match: si hay un snapshot Excel con >=80% de headers en común,
        # heredar sus prompts aprendidos en lugar de empezar desde cero.
        fuzzy_source = find_similar_excel_snapshot(db, tenant_id, fp)
        if fuzzy_source:
            source_cfg = _snapshot_recipe_config(fuzzy_source)
            if source_cfg.get("prompt_system"):
                prompts["prompt_system"] = source_cfg["prompt_system"]
            if source_cfg.get("prompt_user"):
                prompts["prompt_user"] = source_cfg["prompt_user"]
            extra_content["fuzzy_source_snapshot_id"] = str(fuzzy_source.id)
        name = f"auto-excel-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
        recipe_name, snap = _create_recipe_and_snapshot(
            db,
            tenant_id,
            name,
            "Generada automáticamente por fingerprint de cabeceras Excel",
            fp,
            fp_hash,
            prompts,
            extra_content,
            created_by,
        )
        created = True
        db.commit()
    recipe_config = _snapshot_recipe_config(snap)
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
    snap = None if force_new else find_snapshot_by_hash(db, tenant_id, fp_hash, fingerprint=fp)
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

    recipe_config = _snapshot_recipe_config(snap)
    return recipe_config, snap.id, "auto_text_fingerprint", was_created, recipe_name
