"""API endpoints for Recipes and /run (Importador v1.3).

Business Rules:
  RB-01  Templates are non-blocking – /run always works without a recipe.
  RB-02  Zero-Shot fallback when no recipe context is provided.
  RB-03  Every execution stores a recipe_snapshot reference for traceability.
  RB-04  Drafts vs Snapshots – drafts are editable, snapshots immutable.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope

from . import crud, recipe_crud
from .ai_classifier import analyze_document
from .api_lifecycle import mark_legacy_processing_endpoint
from .auto_recipe import should_reprocess_existing_document
from .document_fields import safe_floatish
from .ocr_service import detect_file_type, extract_text_from_file, iter_zip_entries
from .processing_service import RecipeContext, process_import_document
from .schemas import (
    DraftCreate,
    DraftOut,
    DraftUpdate,
    RecipeCreate,
    RecipeOut,
    RecipeUpdate,
    RunResponse,
    SnapshotOut,
)
from .snapshot_learning import bootstrap_learning_from_existing_document

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


def _has_explicit_recipe_context(
    recipe_id: UUID | None,
    recipe_snapshot_id: UUID | None,
    recipe_draft_json: str | None,
) -> bool:
    return bool(
        recipe_id or recipe_snapshot_id or (recipe_draft_json and str(recipe_draft_json).strip())
    )


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
            draft_data = (
                _json.loads(recipe_draft_json)
                if isinstance(recipe_draft_json, str)
                else recipe_draft_json
            )
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


@router.post("/run", dependencies=protected, deprecated=True, include_in_schema=False)
async def run_import_legacy_disabled():
    raise HTTPException(
        status_code=410,
        detail=(
            "Endpoint legacy deshabilitado. Usa /api/v1/importador/run-async como unica "
            "entrada de importacion."
        ),
    )


async def run_import(
    request: Request,
    response: Response,
    files: list[UploadFile] = File(...),
    recipe_id: UUID | None = Form(default=None),
    recipe_snapshot_id: UUID | None = Form(default=None),
    recipe_draft: str | None = Form(default=None),
    force: bool = Form(default=False),
    db: Session = Depends(get_db),
):
    """Legacy sync recipe path. Prefer /importador/run-async for the production flow.

    CA-01: Works without any recipe selection.
    CA-02: Resolves prompt config: snapshot > draft > recipe_id > zero_shot.
    CA-03: Persists configuration used (model, prompts, raw response).
    """
    tenant_id = _tenant_id(request)
    user_id = _user_id(request)
    mark_legacy_processing_endpoint(response)
    logger.info("Legacy importador endpoint used: /run tenant=%s", tenant_id)

    # Resolve recipe (never fails — always falls back to zero_shot)
    recipe_config, resolution_mode, resolved_snapshot_id = _resolve_recipe_config(
        db,
        recipe_id,
        recipe_snapshot_id,
        recipe_draft,
    )
    explicit_recipe_context = _has_explicit_recipe_context(
        recipe_id, recipe_snapshot_id, recipe_draft
    )
    force_clean_reimport = force and not explicit_recipe_context

    results: list[RunResponse] = []

    async def _process_single(file_bytes: bytes, filename: str, tipo_archivo: str | None = None):
        nonlocal db, tenant_id, user_id, recipe_config, resolution_mode, resolved_snapshot_id, results
        tipo_archivo = tipo_archivo or detect_file_type(filename, db)
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        existing = crud.find_existing_documento(db, tenant_id, filename, len(file_bytes), file_hash)
        exact_hash_match = bool(existing and existing.hash_sha256 == file_hash)
        learning_reprocess_needed = False
        if (
            existing
            and isinstance(getattr(existing, "datos_confirmados", None), dict)
            and existing.datos_confirmados
        ):
            bootstrap_learning_from_existing_document(db, existing, user_id)
        if existing:
            learning_reprocess_needed = bool(
                exact_hash_match
                and existing.estado in ("CONFIRMED", "REVIEW")
                and should_reprocess_existing_document(db, existing)
            )
        reuse_existing = bool(
            existing
            and (
                existing.estado in ("PENDING", "PROCESSING")
                or (
                    existing.estado in ("CONFIRMED", "REVIEW")
                    and not force
                    and not learning_reprocess_needed
                )
            )
        )
        if reuse_existing:
            crud.add_log(
                db,
                existing.id,
                "SKIP_DUPLICATE",
                user_id,
                {
                    "reason": "same hash_or_name",
                    "recipe_resolution": resolution_mode,
                },
            )
            db.commit()
            results.append(
                RunResponse(
                    id=existing.id,
                    estado=existing.estado,
                    tipo_documento_detectado=existing.tipo_documento_detectado,
                    confianza_clasificacion=existing.confianza_clasificacion,
                    requiere_revision=existing.requiere_revision,
                    datos_extraidos=existing.datos_extraidos,
                    llm_model=existing.llm_model,
                    recipe_used=resolution_mode,
                    recipe_snapshot_id=existing.recipe_snapshot_id,
                )
            )
            return

        predecessor = None
        rerun_reason = "new_upload"
        if (
            exact_hash_match
            and existing
            and (
                existing.estado == "FAILED"
                or (existing.estado in ("CONFIRMED", "REVIEW") and force)
                or (existing.estado == "REVIEW" and not reuse_existing)
            )
        ):
            doc = existing
            rerun_reason = (
                "learning_update" if learning_reprocess_needed and not force else "manual"
            )
            crud.reset_documento_for_reprocess(
                db,
                doc,
                estado="PROCESSING",
                recipe_snapshot_id=resolved_snapshot_id,
                clear_recipe_snapshot=resolved_snapshot_id is None,
            )
        else:
            predecessor = crud.find_latest_documento_by_name(
                db,
                tenant_id,
                filename,
                exclude_hash_sha256=file_hash,
            )
            doc = crud.create_documento(
                db,
                {
                    "tenant_id": tenant_id,
                    "nombre_archivo": filename,
                    "tipo_archivo": tipo_archivo,
                    "tamanio_bytes": len(file_bytes),
                    "hash_sha256": file_hash,
                    "estado": "PROCESSING",
                    "usuario_id": user_id,
                    "recipe_snapshot_id": resolved_snapshot_id,
                },
            )
            if predecessor and predecessor.id != doc.id:
                crud.link_documento_successor(db, predecessor.id, doc.id)
        crud.add_log(
            db,
            doc.id,
            "RUN",
            user_id,
            {
                "filename": filename,
                "size": len(file_bytes),
                "force": force,
                "force_clean_reimport": force_clean_reimport,
                "explicit_recipe_context": explicit_recipe_context,
                "recipe_resolution": resolution_mode,
                "recipe_snapshot_id": str(resolved_snapshot_id) if resolved_snapshot_id else None,
                "reason": rerun_reason,
            },
        )
        db.commit()

        try:
            result = await process_import_document(
                mode="run",
                db=db,
                doc=doc,
                tenant_id=tenant_id,
                user_id=user_id,
                file_bytes=file_bytes,
                filename=filename,
                tipo_archivo=tipo_archivo,
                force=force,
                extract_text_fn=extract_text_from_file,
                analyze_document_fn=analyze_document,
                recipe_context=RecipeContext(
                    recipe_config=recipe_config or {},
                    resolution_mode=resolution_mode,
                    resolved_snapshot_id=resolved_snapshot_id,
                    explicit_recipe_context=explicit_recipe_context,
                    force_clean_reimport=force_clean_reimport,
                    recipe_id=recipe_id,
                ),
            )
            db.commit()
            results.append(
                RunResponse(
                    id=doc.id,
                    estado=doc.estado,
                    tipo_documento_detectado=result.tipo_documento_detectado,
                    confianza_clasificacion=result.confianza_clasificacion,
                    requiere_revision=result.requiere_revision,
                    datos_extraidos=result.datos_extraidos,
                    llm_model=result.llm_model,
                    recipe_used=result.recipe_used,
                    recipe_snapshot_id=result.recipe_snapshot_id,
                    auto_recipe_created=result.auto_recipe_created,
                    auto_recipe_name=result.auto_recipe_name,
                )
            )

        except Exception as exc:
            logger.error("Error processing %s: %s", filename, exc)
            crud.update_documento(
                db,
                doc,
                {
                    "estado": "FAILED",
                    "error_detalle": str(exc),
                    "llm_model": "error",
                    "raw_ai_json": {"run": {"used": resolution_mode, "error": str(exc)}},
                },
            )
            crud.add_log(db, doc.id, "ERROR", user_id, {"error": str(exc)})
            db.commit()
            results.append(RunResponse(id=doc.id, estado="FAILED", recipe_used=resolution_mode))

    _max_file_mb = max(1, int((os.getenv("IMPORTS_MAX_FILE_SIZE_MB") or "16").strip() or "16"))
    _max_file_bytes = _max_file_mb * 1024 * 1024

    tasks: list[tuple[bytes, str, str]] = []

    for file in files:
        filename = (file.filename or "sin_nombre").strip()

        # Saltar archivos temporales de Office y otros no válidos
        if (
            not filename
            or filename.startswith("~$")
            or filename.lower() in {"thumbs.db", ".ds_store"}
        ):
            logger.info("/run: saltando archivo temporal: %s", filename)
            continue

        file_bytes = await file.read()
        if not file_bytes:
            continue

        tipo_archivo = detect_file_type(filename, db)

        # Excel/XLS: sin límite de tamaño — openpyxl read_only ignora imágenes
        # embebidas y los row-limits de _extract_excel acotan la memoria real usada.
        # PDF/imágenes/otros: el tamaño sí correlaciona con tiempo de OCR y RAM.
        _es_excel = tipo_archivo in ("XLSX", "XLS")
        if not _es_excel and len(file_bytes) > _max_file_bytes:
            size_mb = len(file_bytes) / (1024 * 1024)
            doc_err = crud.create_documento(
                db,
                {
                    "tenant_id": tenant_id,
                    "nombre_archivo": filename,
                    "tipo_archivo": tipo_archivo,
                    "tamanio_bytes": len(file_bytes),
                    "hash_sha256": hashlib.sha256(file_bytes).hexdigest(),
                    "estado": "FAILED",
                    "usuario_id": user_id,
                    "recipe_snapshot_id": resolved_snapshot_id,
                    "error_detalle": (
                        f"Archivo demasiado grande: {size_mb:.0f} MB "
                        f"(límite: {_max_file_mb} MB)."
                    ),
                },
            )
            crud.add_log(
                db,
                doc_err.id,
                "ERROR",
                user_id,
                {
                    "error": "size_limit_exceeded",
                    "size_mb": round(size_mb, 1),
                    "limit_mb": _max_file_mb,
                },
            )
            db.commit()
            results.append(RunResponse(id=doc_err.id, estado="FAILED", recipe_used=resolution_mode))
            continue

        if tipo_archivo == "ZIP":
            entries = list(iter_zip_entries(file_bytes, db=db))
            if not entries:
                doc = crud.create_documento(
                    db,
                    {
                        "tenant_id": tenant_id,
                        "nombre_archivo": filename,
                        "tipo_archivo": tipo_archivo,
                        "tamanio_bytes": len(file_bytes),
                        "estado": "FAILED",
                        "usuario_id": user_id,
                        "recipe_snapshot_id": resolved_snapshot_id,
                        "error_detalle": "ZIP vacío o sin ficheros soportados",
                    },
                )
                crud.add_log(
                    db,
                    doc.id,
                    "RUN",
                    user_id,
                    {
                        "filename": filename,
                        "size": len(file_bytes),
                        "recipe_resolution": resolution_mode,
                        "recipe_snapshot_id": (
                            str(resolved_snapshot_id) if resolved_snapshot_id else None
                        ),
                    },
                )
                crud.add_log(
                    db, doc.id, "ERROR", user_id, {"error": "ZIP vacío o sin ficheros soportados"}
                )
                db.commit()
                results.append(RunResponse(id=doc.id, estado="FAILED", recipe_used=resolution_mode))
                continue
            for inner_name, inner_bytes in entries:
                tasks.append(
                    (inner_bytes, f"{filename}::{inner_name}", detect_file_type(inner_name, db))
                )
        else:
            tasks.append((file_bytes, filename, tipo_archivo))

    # Procesar todos los archivos en paralelo; las llamadas AI se serializan
    # internamente via semáforo (Ollama) o van en paralelo real (OpenAI).
    await asyncio.gather(*(_process_single(fb, fn, ta) for fb, fn, ta in tasks))

    return results


# =====================================================================
#  Recipe CRUD
# =====================================================================


@router.post("/recipes", response_model=RecipeOut, dependencies=protected)
def create_recipe(body: RecipeCreate, request: Request, db: Session = Depends(get_db)):
    recipe = recipe_crud.create_recipe(
        db,
        {
            "tenant_id": _tenant_id(request),
            "name": body.name,
            "description": body.description,
            "is_public": body.is_public,
            "created_by": _user_id(request),
        },
    )
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
def update_recipe(
    recipe_id: UUID, body: RecipeUpdate, request: Request, db: Session = Depends(get_db)
):
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
def create_draft(
    recipe_id: UUID, body: DraftCreate, request: Request, db: Session = Depends(get_db)
):
    recipe = recipe_crud.get_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(404, "Receta no encontrada")
    draft = recipe_crud.create_draft(
        db,
        {
            "tenant_id": _tenant_id(request),
            "recipe_id": recipe_id,
            "prompt_system": body.prompt_system,
            "prompt_user": body.prompt_user,
            "model_config": body.ai_model_config,
            "updated_by": _user_id(request),
        },
    )
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
def update_draft(
    draft_id: UUID, body: DraftUpdate, request: Request, db: Session = Depends(get_db)
):
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
def create_snapshot(
    draft_id: UUID,
    request: Request,
    version_tag: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Create an immutable snapshot from a draft (RB-03, RB-04)."""
    draft = recipe_crud.get_draft(db, draft_id)
    if not draft:
        raise HTTPException(404, "Borrador no encontrado")
    content = {
        "prompt_system": draft.prompt_system,
        "prompt_user": draft.prompt_user,
        "model_config": draft.model_config,
    }
    prev = recipe_crud.get_latest_snapshot(db, draft.recipe_id)
    if prev and prev.content_json:
        if prev.content_json.get("fingerprint_hash"):
            content["fingerprint_hash"] = prev.content_json["fingerprint_hash"]
        if prev.content_json.get("fingerprint"):
            content["fingerprint"] = prev.content_json["fingerprint"]
    snap = recipe_crud.create_snapshot(
        db,
        {
            "tenant_id": _tenant_id(request),
            "recipe_id": draft.recipe_id,
            "draft_id": draft_id,
            "version_tag": version_tag,
            "content_json": content,
            "created_by": _user_id(request),
        },
    )
    db.commit()
    return snap


@router.get(
    "/recipes/{recipe_id}/snapshots", response_model=list[SnapshotOut], dependencies=protected
)
def list_snapshots(recipe_id: UUID, request: Request, db: Session = Depends(get_db)):
    return recipe_crud.list_snapshots(db, recipe_id)


@router.get("/snapshots/{snapshot_id}", response_model=SnapshotOut, dependencies=protected)
def get_snapshot(snapshot_id: UUID, request: Request, db: Session = Depends(get_db)):
    snap = recipe_crud.get_snapshot(db, snapshot_id)
    if not snap:
        raise HTTPException(404, "Snapshot no encontrado")
    return snap


@router.get("/save-capabilities", dependencies=protected)
def get_save_capabilities(request: Request, db: Session = Depends(get_db)):
    """Return which modules are active for the tenant, for save button visibility."""
    from app.models.core.module import CompanyModule, Module

    tenant_id = _tenant_id(request)
    relevant = {"purchases", "expenses", "inventory", "invoicing", "accounting", "suppliers"}
    # Map Spanish module names to English capability keys
    _es_to_en: dict[str, list[str]] = {
        "compras": ["purchases"],
        "gastos": ["expenses"],
        "inventario": ["inventory"],
        "facturación": ["invoicing"],
        "facturacion": ["invoicing"],
        "contabilidad": ["accounting"],
        "proveedores": ["suppliers"],
    }
    rows = (
        db.query(Module.name)
        .join(CompanyModule, CompanyModule.module_id == Module.id)
        .filter(CompanyModule.tenant_id == tenant_id, CompanyModule.active.is_(True))
        .all()
    )
    active_names = {name.lower().strip() for (name,) in rows}
    # Resolve Spanish names to English capability keys
    resolved: set[str] = set()
    for name in active_names:
        resolved.add(name)
        if name in _es_to_en:
            resolved.update(_es_to_en[name])
    return {mod: mod in resolved or any(mod in n for n in resolved) for mod in relevant}


def _safe_float(val) -> float | None:
    return safe_floatish(val)
