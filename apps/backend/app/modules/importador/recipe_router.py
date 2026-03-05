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
from .ai_classifier import CONFIDENCE_THRESHOLD, analyze_document
from .ocr_service import detect_file_type, extract_text_from_file, iter_zip_entries
from .auto_recipe import resolve_auto_recipe, resolve_auto_recipe_from_text
import hashlib
import datetime
from .schemas import (
    DraftCreate, DraftOut, DraftUpdate,
    RecipeCreate, RecipeOut, RecipeUpdate,
    RunResponse, SnapshotOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/importador", tags=["Importador v1.3"])
protected = [Depends(with_access_claims), Depends(require_scope("tenant"))]


def _json_safe(obj):
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    return obj


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
    force: bool = Form(default=False),
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

    async def _process_single(file_bytes: bytes, filename: str, tipo_archivo: str | None = None):
        nonlocal db, tenant_id, user_id, recipe_config, resolution_mode, resolved_snapshot_id, results
        tipo_archivo = tipo_archivo or detect_file_type(filename)
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        existing = None if force else crud.find_existing_documento(db, tenant_id, filename, len(file_bytes), file_hash)
        if existing and existing.estado in ("CONFIRMED", "REVIEW"):
            crud.add_log(db, existing.id, "SKIP_DUPLICATE", user_id, {
                "reason": "same hash_or_name",
                "recipe_resolution": resolution_mode,
            })
            db.commit()
            results.append(RunResponse(
                id=existing.id,
                estado=existing.estado,
                tipo_documento_detectado=existing.tipo_documento_detectado,
                confianza_clasificacion=existing.confianza_clasificacion,
                requiere_revision=existing.requiere_revision,
                datos_extraidos=existing.datos_extraidos,
                llm_model=existing.llm_model,
                recipe_used=resolution_mode,
                recipe_snapshot_id=existing.recipe_snapshot_id,
            ))
            return

        doc = crud.create_documento(db, {
            "tenant_id": tenant_id,
            "nombre_archivo": filename,
            "tipo_archivo": tipo_archivo,
            "tamanio_bytes": len(file_bytes),
            "hash_sha256": file_hash,
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
            extraction = await extract_text_from_file(file_bytes, filename)
            text = extraction.get("text", "")
            structured = extraction.get("structured_data")
            sheet_profiles = extraction.get("sheet_profiles")
            headers_lower = []
            if sheet_profiles and isinstance(sheet_profiles, dict):
                for prof in sheet_profiles.values():
                    headers_lower.extend([h.lower() for h in prof.get("headers", [])])

            # Auto recipe si zero-shot y tenemos cabeceras Excel
            local_recipe_config = recipe_config
            local_resolution = resolution_mode
            local_snapshot_id = resolved_snapshot_id
            local_auto_created = False
            local_auto_name: str | None = None
            if resolution_mode == "zero_shot" and not resolved_snapshot_id and sheet_profiles:
                local_recipe_config, local_snapshot_id, local_resolution, local_auto_created, local_auto_name = resolve_auto_recipe(
                    db, tenant_id, sheet_profiles, user_id
                )

            # Preparar contenido para el LLM
            has_structured = bool(structured and isinstance(structured, list) and sheet_profiles)
            if has_structured:
                # Excel/CSV: enviar cabeceras + muestra de filas al LLM
                # headers_norm = claves normalizadas que usan los dicts de filas ("precio_unitario_venta")
                # headers_display = nombres legibles para mostrar ("PRECIO UNITARIO VENTA")
                headers_norm: list[str] = []
                headers_display: list[str] = []
                for prof in sheet_profiles.values():
                    headers_norm = prof.get("headers_norm") or []
                    headers_display = prof.get("headers") or headers_norm
                    break
                headers = headers_norm  # alias para compatibilidad
                sample_lines = [f"Columnas: {headers_display}"]
                for row in (structured[:15] if isinstance(structured, list) else []):
                    if isinstance(row, dict):
                        sample_lines.append(str({k: v for k, v in row.items() if not k.startswith("_")}))
                    else:
                        sample_lines.append(str(row))
                llm_content = "\n".join(sample_lines)
            else:
                llm_content = text[:4000] if text else ""

            # Una sola llamada LLM: clasifica + extrae (sin reglas hardcodeadas)
            analysis = await analyze_document(
                llm_content, filename, extraction.get("format", tipo_archivo),
                has_structured_rows=has_structured,
                recipe_config=local_recipe_config,
            )

            tipo_doc = analysis.get("tipo_documento", "OTRO")
            confianza = float(analysis.get("confianza", 0.0))
            requiere_revision = confianza < CONFIDENCE_THRESHOLD
            es_tabla = analysis.get("es_tabla", False)

            extraction_raw = {
                "_raw_response": analysis.get("raw_response"),
                "_model_used": analysis.get("model_used"),
                "_prompt_sent": analysis.get("prompt_sent"),
            }

            # Construir datos_extraidos
            if es_tabla and has_structured:
                # Tabla con filas ya parseadas: usar structured_data directamente
                # columnas usa headers_display para mostrar nombres bonitos en la UI
                # Las filas usan headers_norm como claves (deben coincidir con lo que guarda ocr_service)
                columnas = headers_display or headers_norm
                datos_extraidos = {"filas": structured[:200], "total_filas": len(structured), "columnas": columnas, "columnas_norm": headers_norm}
            else:
                # Documento único o tabla detectada por LLM en texto (PDF, etc.)
                datos_extraidos = analysis.get("campos") or {}

            # Para PDF/XML/imagen/TXT: crear fingerprint post-extracción para futuros imports similares
            auto_recipe_created = False
            auto_recipe_name: str | None = None
            if not sheet_profiles and tipo_doc != "OTRO":
                _, post_snap_id, _, auto_recipe_created, auto_recipe_name = resolve_auto_recipe_from_text(
                    db, tenant_id, tipo_doc, datos_extraidos,
                    extraction.get("format", tipo_archivo),
                    user_id,
                )
                if post_snap_id and not local_snapshot_id:
                    local_snapshot_id = post_snap_id

            model_used = analysis.get("model_used") or "unknown"
            raw_ai_json = {
                "run": {
                    "recipe_resolution": {
                        "recipe_id": str(recipe_id) if recipe_id else None,
                        "recipe_snapshot_id": str(local_snapshot_id or resolved_snapshot_id) if (local_snapshot_id or resolved_snapshot_id) else None,
                        "used": local_resolution,
                    },
                    "model": model_used,
                },
                "analysis": {
                    "prompt": analysis.get("prompt_sent", ""),
                    "raw_response": analysis.get("raw_response", ""),
                    "parsed": {
                        "tipo_documento": tipo_doc,
                        "confianza": confianza,
                        "razonamiento": analysis.get("razonamiento", ""),
                        "es_tabla": es_tabla,
                    },
                    "campos_extraidos": list(datos_extraidos.keys()) if isinstance(datos_extraidos, dict) else [],
                },
            }

            datos_extraidos = _json_safe(datos_extraidos) if isinstance(datos_extraidos, (dict, list)) else datos_extraidos
            sheet_profiles = _json_safe(sheet_profiles) if isinstance(sheet_profiles, (dict, list)) else sheet_profiles
            raw_ai_json = _json_safe(raw_ai_json)

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
                "fingerprint_json": sheet_profiles,
                "sheet_profiles_json": sheet_profiles,
                "recipe_snapshot_id": local_snapshot_id or resolved_snapshot_id,
            })
            crud.add_log(db, doc.id, "EXTRACT", user_id, {
                "campos_extraidos": list(datos_extraidos.keys()) if isinstance(datos_extraidos, dict) else [],
                "model": model_used,
                "recipe_mode": local_resolution,
                "auto_recipe_created": auto_recipe_created,
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
                recipe_used=local_resolution,
                recipe_snapshot_id=local_snapshot_id or resolved_snapshot_id,
                auto_recipe_created=auto_recipe_created or None,
                auto_recipe_name=auto_recipe_name,
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

    for file in files:
        file_bytes = await file.read()
        filename = file.filename or "sin_nombre"
        tipo_archivo = detect_file_type(filename)

        if tipo_archivo == "ZIP":
            entries = list(iter_zip_entries(file_bytes))
            if not entries:
                doc = crud.create_documento(db, {
                    "tenant_id": tenant_id,
                    "nombre_archivo": filename,
                    "tipo_archivo": tipo_archivo,
                    "tamanio_bytes": len(file_bytes),
                    "estado": "FAILED",
                    "usuario_id": user_id,
                    "recipe_snapshot_id": resolved_snapshot_id,
                    "error_detalle": "ZIP vacío o sin ficheros soportados",
                })
                crud.add_log(db, doc.id, "RUN", user_id, {
                    "filename": filename,
                    "size": len(file_bytes),
                    "recipe_resolution": resolution_mode,
                    "recipe_snapshot_id": str(resolved_snapshot_id) if resolved_snapshot_id else None,
                })
                crud.add_log(db, doc.id, "ERROR", user_id, {"error": "ZIP vacío o sin ficheros soportados"})
                db.commit()
                results.append(RunResponse(id=doc.id, estado="FAILED", recipe_used=resolution_mode))
                continue
            for inner_name, inner_bytes in entries:
                await _process_single(inner_bytes, f"{filename}::{inner_name}", detect_file_type(inner_name))
        else:
            await _process_single(file_bytes, filename, tipo_archivo)

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
