"""API endpoints for Recipes and /run (Importador v1.3).

Business Rules:
  RB-01  Templates are non-blocking – /run always works without a recipe.
  RB-02  Zero-Shot fallback when no recipe context is provided.
  RB-03  Every execution stores a recipe_snapshot reference for traceability.
  RB-04  Drafts vs Snapshots – drafts are editable, snapshots immutable.
"""
from __future__ import annotations
import logging
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from . import crud, recipe_crud
from .ai_classifier import CONFIDENCE_THRESHOLD, classify_document, extract_fields
from .ocr_service import detect_file_type, extract_text_from_file
from .schemas import (
    DraftCreate, DraftOut, DraftUpdate,
    RecipeCreate, RecipeOut, RecipeUpdate,
    RunResponse, SnapshotOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/importador", tags=["Importador v1.3"])
protected = [Depends(with_access_claims), Depends(require_scope("tenant"))]


def _tenant_id(request: Request) -> UUID:
    claims = getattr(request.state, "access_claims", None) or {}
    tid = claims.get("tenant_id") or getattr(request.state, "tenant_id", None)
    if not tid:
        raise HTTPException(status_code=401, detail="tenant_id no disponible")
    return UUID(str(tid)) if not isinstance(tid, UUID) else tid


def _user_id(request: Request) -> str:
    claims = getattr(request.state, "access_claims", None) or {}
    return str(claims.get("user_id", "unknown"))


# =====================================================================
#  POST /run  — Core processing endpoint (RB-01: never requires recipe)
# =====================================================================

def _resolve_recipe_config(
    db: Session,
    recipe_id: UUID | None,
    recipe_snapshot_id: UUID | None,
    recipe_draft_json: str | None,
) -> tuple[dict, str, UUID | None]:
    """Resolve recipe configuration with CA-02 priority order.
    
    Returns: (config_dict, resolution_mode, snapshot_id_or_None)
    Priority: snapshot_id > draft_json > recipe_id(latest snapshot) > zero_shot
    """
    import json as _json

    # 1. Explicit snapshot
    if recipe_snapshot_id:
        snap = recipe_crud.get_snapshot(db, recipe_snapshot_id)
        if snap:
            return snap.content_json or {}, "snapshot", snap.id
        logger.warning("Snapshot %s not found, falling back to zero-shot", recipe_snapshot_id)

    # 2. Inline draft (ephemeral, not persisted)
    if recipe_draft_json:
        try:
            draft_data = _json.loads(recipe_draft_json) if isinstance(recipe_draft_json, str) else recipe_draft_json
            return draft_data, "draft", None
        except (ValueError, TypeError):
            logger.warning("Invalid recipe_draft JSON, falling back to zero-shot")

    # 3. recipe_id → latest snapshot
    if recipe_id:
        snap = recipe_crud.get_latest_snapshot(db, recipe_id)
        if snap:
            return snap.content_json or {}, "recipe_latest", snap.id
        logger.warning("No snapshots for recipe %s, falling back to zero-shot", recipe_id)

    # 4. Zero-shot default (RB-02)
    return {}, "zero_shot", None


@router.post("/run", response_model=list[RunResponse], dependencies=protected)
async def run_import(
    request: Request,
    files: list[UploadFile] = File(...),
    recipe_id: UUID | None = Form(default=None),
    recipe_snapshot_id: UUID | None = Form(default=None),
    recipe_draft: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    """Process files with optional recipe. RB-01: recipe is NEVER required.
    
    CA-01: Works without any recipe selection.
    CA-02: Resolves prompt config: snapshot > draft > recipe_id > zero_shot.
    CA-03: Persists configuration used (model, prompts, raw response).
    """
    tenant_id = _tenant_id(request)
    user_id = _user_id(request)

    # Resolve recipe (never fails — always falls back to zero_shot)
    recipe_config, resolution_mode, resolved_snapshot_id = _resolve_recipe_config(
        db, recipe_id, recipe_snapshot_id, recipe_draft,
    )

    results: list[RunResponse] = []

    for file in files:
        file_bytes = await file.read()
        filename = file.filename or "sin_nombre"
        tipo_archivo = detect_file_type(filename)

        # Create document record
        doc = crud.create_documento(db, {
            "tenant_id": tenant_id,
            "nombre_archivo": filename,
            "tipo_archivo": tipo_archivo,
            "tamanio_bytes": len(file_bytes),
            "estado": "PROCESSING",
            "usuario_id": user_id,
            "recipe_snapshot_id": resolved_snapshot_id,
        })
        crud.add_log(db, doc.id, "RUN", user_id, {
            "filename": filename,
            "size": len(file_bytes),
            "recipe_resolution": resolution_mode,
            "recipe_snapshot_id": str(resolved_snapshot_id) if resolved_snapshot_id else None,
        })
        db.commit()

        try:
            # 1. Extract text/data (OCR)
            extraction = await extract_text_from_file(file_bytes, filename)
            text = extraction.get("text", "")
            structured = extraction.get("structured_data")

            # Si es XLS/CSV y no hay texto OCR, genera texto a partir de las filas para alimentar a la IA
            text_for_llm = text
            if (not text or text.isspace()) and structured and isinstance(structured, list):
                # Tomamos hasta 100 filas para evitar prompts enormes
                sample_rows = structured[:100]
                lines: list[str] = []
                for row in sample_rows:
                    if isinstance(row, (list, tuple)):
                        lines.append(",".join("" if v is None else str(v) for v in row))
                    elif isinstance(row, dict):
                        # Si viene como dict fila-columna
                        lines.append(",".join(f"{k}={v}" for k, v in row.items()))
                    else:
                        lines.append(str(row))
                text_for_llm = "\n".join(lines)

            # 2. Classify (with recipe config)
            classification = await classify_document(
                text or text_for_llm, filename, extraction.get("format", ""),
                recipe_config=recipe_config,
            )
            tipo_doc = classification.get("tipo_documento", "OTRO")
            confianza = float(classification.get("confianza", 0.0))
            requiere_revision = confianza < CONFIDENCE_THRESHOLD

            # 3. Extract fields (with recipe config)
            datos_extraidos = await extract_fields(text_for_llm or text, tipo_doc, filename, recipe_config=recipe_config)
            extraction_raw = {
                "_raw_response": datos_extraidos.pop("_raw_response", None),
                "_model_used": datos_extraidos.pop("_model_used", None),
                "_prompt_sent": datos_extraidos.pop("_prompt_sent", None),
            }

            # Adjunta una muestra de filas estructuradas para referencia/manual review si existe
            if structured and isinstance(structured, list):
                datos_extraidos.setdefault("_structured_preview", structured[:50])
                datos_extraidos.setdefault("_structured_total_filas", len(structured))

            # Build raw_ai_json for traceability (CA-03)
            model_used = classification.get("model_used") or extraction_raw.get("_model_used") or "unknown"
            raw_ai_json = {
                "run": {
                    "recipe_resolution": {
                        "recipe_id": str(recipe_id) if recipe_id else None,
                        "recipe_snapshot_id": str(resolved_snapshot_id) if resolved_snapshot_id else None,
                        "used": resolution_mode,
                    },
                    "model": model_used,
                },
                "classification": {
                    "prompt": classification.get("prompt_sent", ""),
                    "raw_response": classification.get("raw_response", ""),
                    "parsed": {
                        "tipo_documento": tipo_doc,
                        "confianza": confianza,
                        "razonamiento": classification.get("razonamiento", ""),
                    },
                },
                "extraction": {
                    "prompt": extraction_raw.get("_prompt_sent", ""),
                    "raw_response": extraction_raw.get("_raw_response", ""),
                    "campos_extraidos": list(datos_extraidos.keys()) if isinstance(datos_extraidos, dict) else [],
                },
            }

            # Update document
            crud.update_documento(db, doc, {
                "texto_ocr": text[:50000],
                "tipo_documento_detectado": tipo_doc,
                "confianza_clasificacion": confianza,
                "requiere_revision": requiere_revision,
                "datos_extraidos": datos_extraidos,
                "estado": "REVIEW",
                "proveedor_detectado": datos_extraidos.get("proveedor") if isinstance(datos_extraidos, dict) else None,
                "ruc_detectado": datos_extraidos.get("ruc") if isinstance(datos_extraidos, dict) else None,
                "monto_total": _safe_float(datos_extraidos.get("monto_total") if isinstance(datos_extraidos, dict) else None),
                "moneda": datos_extraidos.get("moneda") if isinstance(datos_extraidos, dict) else None,
                "fecha_documento": datos_extraidos.get("fecha") if isinstance(datos_extraidos, dict) else None,
                "llm_model": model_used,
                "raw_ai_json": raw_ai_json,
            })
            crud.add_log(db, doc.id, "EXTRACT", user_id, {
                "campos_extraidos": list(datos_extraidos.keys()) if isinstance(datos_extraidos, dict) else [],
                "model": model_used,
                "recipe_mode": resolution_mode,
            })
            db.commit()

            results.append(RunResponse(
                id=doc.id,
                estado=doc.estado,
                tipo_documento_detectado=tipo_doc,
                confianza_clasificacion=confianza,
                requiere_revision=requiere_revision,
                datos_extraidos=datos_extraidos,
                llm_model=model_used,
                recipe_used=resolution_mode,
                recipe_snapshot_id=resolved_snapshot_id,
            ))

        except Exception as exc:
            logger.error("Error processing %s: %s", filename, exc)
            crud.update_documento(db, doc, {
                "estado": "FAILED",
                "error_detalle": str(exc),
                "llm_model": "error",
                "raw_ai_json": {"run": {"used": resolution_mode, "error": str(exc)}},
            })
            crud.add_log(db, doc.id, "ERROR", user_id, {"error": str(exc)})
            db.commit()
            results.append(RunResponse(id=doc.id, estado="FAILED", recipe_used=resolution_mode))

    return results


# =====================================================================
#  Recipe CRUD
# =====================================================================

@router.post("/recipes", response_model=RecipeOut, dependencies=protected)
def create_recipe(body: RecipeCreate, request: Request, db: Session = Depends(get_db)):
    recipe = recipe_crud.create_recipe(db, {
        "tenant_id": _tenant_id(request),
        "name": body.name,
        "description": body.description,
        "is_public": body.is_public,
        "created_by": _user_id(request),
    })
    db.commit()
    return recipe


@router.get("/recipes", response_model=list[RecipeOut], dependencies=protected)
def list_recipes(
    request: Request,
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    return recipe_crud.list_recipes(db, _tenant_id(request), include_archived=include_archived)


@router.get("/recipes/{recipe_id}", response_model=RecipeOut, dependencies=protected)
def get_recipe(recipe_id: UUID, request: Request, db: Session = Depends(get_db)):
    recipe = recipe_crud.get_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(404, "Receta no encontrada")
    return recipe


@router.patch("/recipes/{recipe_id}", response_model=RecipeOut, dependencies=protected)
def update_recipe(recipe_id: UUID, body: RecipeUpdate, request: Request, db: Session = Depends(get_db)):
    recipe = recipe_crud.get_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(404, "Receta no encontrada")
    recipe_crud.update_recipe(db, recipe, body.model_dump(exclude_unset=True))
    db.commit()
    return recipe


# =====================================================================
#  Draft CRUD
# =====================================================================

@router.post("/recipes/{recipe_id}/drafts", response_model=DraftOut, dependencies=protected)
def create_draft(recipe_id: UUID, body: DraftCreate, request: Request, db: Session = Depends(get_db)):
    recipe = recipe_crud.get_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(404, "Receta no encontrada")
    draft = recipe_crud.create_draft(db, {
        "tenant_id": _tenant_id(request),
        "recipe_id": recipe_id,
        "prompt_system": body.prompt_system,
        "prompt_user": body.prompt_user,
        "model_config": body.ai_model_config,
        "updated_by": _user_id(request),
    })
    db.commit()
    return draft


@router.get("/recipes/{recipe_id}/drafts", response_model=list[DraftOut], dependencies=protected)
def list_drafts(recipe_id: UUID, request: Request, db: Session = Depends(get_db)):
    return recipe_crud.list_drafts(db, recipe_id)


@router.get("/drafts/{draft_id}", response_model=DraftOut, dependencies=protected)
def get_draft(draft_id: UUID, request: Request, db: Session = Depends(get_db)):
    draft = recipe_crud.get_draft(db, draft_id)
    if not draft:
        raise HTTPException(404, "Borrador no encontrado")
    return draft


@router.patch("/drafts/{draft_id}", response_model=DraftOut, dependencies=protected)
def update_draft(draft_id: UUID, body: DraftUpdate, request: Request, db: Session = Depends(get_db)):
    draft = recipe_crud.get_draft(db, draft_id)
    if not draft:
        raise HTTPException(404, "Borrador no encontrado")
    data = {}
    if body.prompt_system is not None:
        data["prompt_system"] = body.prompt_system
    if body.prompt_user is not None:
        data["prompt_user"] = body.prompt_user
    if body.ai_model_config is not None:
        data["model_config"] = body.ai_model_config
    data["updated_by"] = _user_id(request)
    recipe_crud.update_draft(db, draft, data)
    db.commit()
    return draft


# =====================================================================
#  Snapshots (immutable — CA-04/CA-05)
# =====================================================================

@router.post("/drafts/{draft_id}/snapshot", response_model=SnapshotOut, dependencies=protected)
def create_snapshot(draft_id: UUID, request: Request, version_tag: str | None = Query(default=None), db: Session = Depends(get_db)):
    """Create an immutable snapshot from a draft (RB-03, RB-04)."""
    draft = recipe_crud.get_draft(db, draft_id)
    if not draft:
        raise HTTPException(404, "Borrador no encontrado")
    content = {
        "prompt_system": draft.prompt_system,
        "prompt_user": draft.prompt_user,
        "model_config": draft.model_config,
    }
    snap = recipe_crud.create_snapshot(db, {
        "tenant_id": _tenant_id(request),
        "recipe_id": draft.recipe_id,
        "draft_id": draft_id,
        "version_tag": version_tag,
        "content_json": content,
        "created_by": _user_id(request),
    })
    db.commit()
    return snap


@router.get("/recipes/{recipe_id}/snapshots", response_model=list[SnapshotOut], dependencies=protected)
def list_snapshots(recipe_id: UUID, request: Request, db: Session = Depends(get_db)):
    return recipe_crud.list_snapshots(db, recipe_id)


@router.get("/snapshots/{snapshot_id}", response_model=SnapshotOut, dependencies=protected)
def get_snapshot(snapshot_id: UUID, request: Request, db: Session = Depends(get_db)):
    snap = recipe_crud.get_snapshot(db, snapshot_id)
    if not snap:
        raise HTTPException(404, "Snapshot no encontrado")
    return snap


def _safe_float(val) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
