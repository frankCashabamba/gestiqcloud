"""API endpoints for Importador Contable Universal."""
from __future__ import annotations
import logging
from uuid import UUID
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from . import crud
from .ai_classifier import CONFIDENCE_THRESHOLD, analyze_document
from .ocr_service import detect_file_type, extract_text_from_file, iter_zip_entries
from .auto_recipe import resolve_auto_recipe
from .recipe_sync import get_available_recipe_sheets, upsert_recipe_from_import
import hashlib
import datetime
from .schemas import (
    ConfirmRequest, DashboardStats, DocumentoDetailOut, DocumentoListOut,
    DocumentoOut, EditFieldsRequest, LogCambioOut, SyncRecipeResponse, SyncRecipesResponse,
    SyncRecipeSheetResponse, UploadResponse,
)
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/importador", tags=["Importador"])
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


def _get_doc_import_data(doc) -> dict:
    data = doc.datos_confirmados or doc.datos_extraidos or {}
    return data if isinstance(data, dict) else {}


def _get_synced_sheet_map(db: Session, doc) -> dict[str, dict]:
    from app.models.recipes import Recipe

    synced: dict[str, dict] = {}
    recipe_to_sheet: dict[str, str] = {}
    candidate_ids: list[UUID] = []
    logs = sorted((getattr(doc, "logs", []) or []), key=lambda log: log.created_at or datetime.datetime.min)
    for log in logs:
        detail = log.detalle or {}
        if log.accion != "SYNC_PRODUCTION" or not isinstance(detail, dict):
            continue
        raw_id = str(detail.get("recipe_id") or "").strip()
        if not raw_id:
            continue
        try:
            candidate_ids.append(UUID(raw_id))
        except ValueError:
            continue

    existing_recipe_ids = {
        str(row[0])
        for row in db.query(Recipe.id)
        .filter(Recipe.tenant_id == doc.tenant_id, Recipe.id.in_(candidate_ids))
        .all()
    } if candidate_ids else set()

    for log in logs:
        if log.accion != "SYNC_PRODUCTION":
            continue
        detail = log.detalle or {}
        if not isinstance(detail, dict):
            continue
        sheet_name = str(detail.get("sheet_used") or "").strip()
        if not sheet_name:
            continue
        raw_recipe_id = str(detail.get("recipe_id") or "").strip()
        if not raw_recipe_id:
            continue
        try:
            recipe_id = str(UUID(raw_recipe_id))
        except ValueError:
            continue
        if recipe_id not in existing_recipe_ids:
            continue
        existing_sheet = recipe_to_sheet.get(recipe_id)
        if existing_sheet and existing_sheet != sheet_name:
            continue
        recipe_to_sheet[recipe_id] = sheet_name
        synced[sheet_name] = {
            "recipe_id": recipe_id,
            "recipe_name": str(detail.get("recipe_name") or "") or None,
            "created_at": log.created_at,
        }
    return synced


@router.post("/upload", response_model=list[UploadResponse], dependencies=protected)
async def upload_files(
    request: Request,
    files: list[UploadFile] = File(...),
    force: bool = Query(default=False, description="Si true, fuerza reprocesar aunque exista duplicado"),
    db: Session = Depends(get_db),
):
    """Upload one or multiple files. Auto-classifies and extracts data."""
    tenant_id = _tenant_id(request)
    user_id = _user_id(request)
    results = []

    async def _process_single(file_bytes: bytes, filename: str, tipo_archivo: str | None = None):
        nonlocal db, tenant_id, user_id, results
        tipo_archivo = tipo_archivo or detect_file_type(filename)
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        existing = None if force else crud.find_existing_documento(db, tenant_id, filename, len(file_bytes), file_hash)
        if existing and existing.estado in ("CONFIRMED", "REVIEW"):
            # Reutiliza resultado anterior para ahorrar tiempo
            crud.add_log(db, existing.id, "SKIP_DUPLICATE", user_id, {"reason": "same hash_or_name"})
            db.commit()
            results.append(UploadResponse(
                id=existing.id,
                estado=existing.estado,
                tipo_documento_detectado=existing.tipo_documento_detectado,
                confianza_clasificacion=existing.confianza_clasificacion,
                requiere_revision=existing.requiere_revision,
                datos_extraidos=existing.datos_extraidos,
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
        })
        crud.add_log(db, doc.id, "UPLOAD", user_id, {"filename": filename, "size": len(file_bytes)})
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

            # Excel/CSV tiene filas ya parseadas — el LLM solo clasifica el tipo, no extrae datos
            has_structured = bool(structured and isinstance(structured, list) and sheet_profiles)

            headers_norm: list[str] = []
            headers_display: list[str] = []
            if has_structured:
                for prof in sheet_profiles.values():
                    headers_norm = prof.get("headers_norm") or []
                    headers_display = prof.get("headers") or headers_norm
                    break

            # Fingerprint para trazabilidad; NO usar el recipe_config guardado para Excel
            # (podría tener prompts de clasificaciones incorrectas anteriores)
            resolved_snapshot_id = None
            resolution_mode = "zero_shot"
            if sheet_profiles:
                _, resolved_snapshot_id, resolution_mode, _, _ = resolve_auto_recipe(
                    db, tenant_id, sheet_profiles, user_id,
                )

            # Contenido para el LLM
            if has_structured:
                sample_lines = [f"Columnas: {headers_display}"]
                for row in (structured[:5] if isinstance(structured, list) else []):
                    if isinstance(row, dict):
                        sample_lines.append(str({k: v for k, v in list(row.items())[:8] if not k.startswith("_")}))
                llm_content = "\n".join(sample_lines)
            else:
                llm_content = text[:4000] if text else ""

            # LLM con prompt genérico limpio (sin recipe_config que pueda sesgar la clasificación)
            analysis = await analyze_document(
                llm_content, filename, extraction.get("format", tipo_archivo),
                has_structured_rows=has_structured,
                recipe_config={},
            )

            tipo_doc = analysis.get("tipo_documento", "OTRO")
            confianza = float(analysis.get("confianza", 0.0))
            requiere_revision = confianza < CONFIDENCE_THRESHOLD

            crud.add_log(db, doc.id, "CLASSIFY", user_id, {
                "tipo_documento": tipo_doc, "confianza": confianza,
                "razonamiento": analysis.get("razonamiento", ""), "model_used": analysis.get("model_used"),
            })

            # Construir datos_extraidos
            if has_structured:
                # Excel/CSV: SIEMPRE filas parseadas — el LLM no decide si es tabla
                sheet_used_str = extraction.get("sheet_used")
                sheet_metadata_raw = extraction.get("sheet_metadata") or {}

                # Agrupar filas por hoja (cada fila tiene _sheet)
                filas_por_hoja_raw: dict[str, list] = {}
                for _row in (structured or []):
                    if isinstance(_row, dict):
                        _sname = str(_row.get("_sheet") or sheet_used_str or "")
                        if _sname:
                            filas_por_hoja_raw.setdefault(_sname, []).append(_row)

                datos_extraidos = {
                    "filas": structured[:200],
                    "total_filas": len(structured),
                    "columnas": headers_display or headers_norm,
                    "columnas_norm": headers_norm,
                    "filas_por_hoja": filas_por_hoja_raw,
                    "metadata_por_hoja": sheet_metadata_raw,
                    "sheet_usada": sheet_used_str,
                }
            else:
                # PDF/imagen/XML/TXT: usar lo que extrajo el LLM
                datos_extraidos = analysis.get("campos") or {}

            crud.add_log(db, doc.id, "EXTRACT", user_id, {"campos_extraidos": list(datos_extraidos.keys()) if isinstance(datos_extraidos, dict) else []})

            datos_extraidos = _json_safe(datos_extraidos) if isinstance(datos_extraidos, (dict, list)) else datos_extraidos
            sheet_profiles = _json_safe(sheet_profiles) if isinstance(sheet_profiles, (dict, list)) else sheet_profiles

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
                "fingerprint_json": sheet_profiles,
                "sheet_profiles_json": sheet_profiles,
                "recipe_snapshot_id": resolved_snapshot_id,
            })
            db.commit()

            results.append(UploadResponse(
                id=doc.id,
                estado=doc.estado,
                tipo_documento_detectado=tipo_doc,
                confianza_clasificacion=confianza,
                requiere_revision=requiere_revision,
                datos_extraidos=datos_extraidos,
            ))
        except Exception as exc:
            logger.error("Error processing %s: %s", filename, exc)
            crud.update_documento(db, doc, {"estado": "FAILED", "error_detalle": str(exc)})
            crud.add_log(db, doc.id, "EXTRACT", user_id, {"error": str(exc)})
            db.commit()
            results.append(UploadResponse(id=doc.id, estado="FAILED"))

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
                    "error_detalle": "ZIP vacío o sin ficheros soportados",
                })
                crud.add_log(db, doc.id, "UPLOAD", user_id, {"filename": filename, "size": len(file_bytes)})
                crud.add_log(db, doc.id, "ERROR", user_id, {"error": "ZIP vacío o sin ficheros soportados"})
                db.commit()
                results.append(UploadResponse(id=doc.id, estado="FAILED", datos_extraidos={"error": "ZIP vacío o sin ficheros soportados"}))
                continue
            for inner_name, inner_bytes in entries:
                await _process_single(inner_bytes, f"{filename}::{inner_name}", detect_file_type(inner_name))
        else:
            await _process_single(file_bytes, filename, tipo_archivo)

    return results


@router.get("/documents", response_model=list[DocumentoListOut], dependencies=protected)
def list_documents(
    request: Request,
    estado: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id(request)
    return crud.list_documentos(db, tenant_id, estado=estado, limit=limit, offset=offset)


@router.get("/documents/{doc_id}", response_model=DocumentoDetailOut, dependencies=protected)
def get_document(doc_id: UUID, request: Request, db: Session = Depends(get_db)):
    from app.models.recipes import Recipe
    doc = crud.get_documento(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    # Si synced_recipe_id apunta a una receta que ya no existe, limpiar la referencia
    if doc.synced_recipe_id:
        exists = db.query(Recipe.id).filter(Recipe.id == doc.synced_recipe_id).first()
        if not exists:
            doc.synced_recipe_id = None
            db.commit()
    doc.synced_sheets = _get_synced_sheet_map(db, doc)
    return doc


class SyncRecipeRequest(BaseModel):
    sheet_usada: str | None = None
    force: bool = False


class SyncRecipesRequest(BaseModel):
    force: bool = False


@router.post("/documents/{doc_id}/confirm", response_model=DocumentoOut, dependencies=protected)
def confirm_document(doc_id: UUID, body: ConfirmRequest, request: Request, db: Session = Depends(get_db)):
    user_id = _user_id(request)
    doc = crud.get_documento(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    if doc.estado == "CONFIRMED":
        raise HTTPException(status_code=400, detail="Documento ya confirmado")

    crud.update_documento(db, doc, {"datos_confirmados": body.datos_confirmados, "estado": "CONFIRMED"})
    crud.add_log(db, doc.id, "CONFIRM", user_id, {"datos_confirmados": body.datos_confirmados})
    db.commit()
    return doc


@router.post("/documents/{doc_id}/sync_recipe", response_model=SyncRecipeResponse, dependencies=protected)
def sync_recipe(doc_id: UUID, body: SyncRecipeRequest | None, request: Request, db: Session = Depends(get_db)):
    from app.models.recipes import Recipe
    user_id = _user_id(request)
    doc = crud.get_documento(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    data = _get_doc_import_data(doc)
    available_sheets = get_available_recipe_sheets(data)
    sheet_override = body.sheet_usada if body else None
    force = bool(body.force) if body else False
    sheet_name = sheet_override or data.get("sheet_usada") or (available_sheets[0] if available_sheets else None)
    synced_sheets = _get_synced_sheet_map(db, doc)

    if sheet_name and sheet_name in synced_sheets and not force:
        raise HTTPException(status_code=409, detail=f"La hoja '{sheet_name}' ya fue sincronizada.")

    recipe_id, was_new = upsert_recipe_from_import(doc, db, sheet_override=sheet_override)
    if not recipe_id:
        raise HTTPException(status_code=422, detail="No se pudo extraer una receta del documento. Verifique que sea un documento de costeo con filas de ingredientes.")

    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()

    # Guardar referencia en el documento
    doc.synced_recipe_id = recipe_id
    crud.add_log(db, doc.id, "SYNC_PRODUCTION", user_id, {
        "recipe_id": str(recipe_id),
        "recipe_name": recipe.name if recipe else None,
        "sheet_used": sheet_name,
        "was_new": was_new,
    })
    db.commit()

    return SyncRecipeResponse(
        recipe_id=recipe_id,
        recipe_name=recipe.name if recipe else "Receta",
        was_new=was_new,
        total_cost=float(recipe.total_cost) if recipe and recipe.total_cost else 0.0,
        ingredients_count=len(recipe.ingredients) if recipe else 0,
    )


@router.post("/documents/{doc_id}/sync_recipes", response_model=SyncRecipesResponse, dependencies=protected)
def sync_recipes(doc_id: UUID, body: SyncRecipesRequest | None, request: Request, db: Session = Depends(get_db)):
    from app.models.recipes import Recipe

    user_id = _user_id(request)
    doc = crud.get_documento(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    data = _get_doc_import_data(doc)
    available_sheets = get_available_recipe_sheets(data)
    if not available_sheets:
        raise HTTPException(status_code=422, detail="El documento no contiene hojas separadas para sincronizar.")

    force = bool(body.force) if body else False
    synced_sheets = _get_synced_sheet_map(db, doc)
    processed_count = 0
    skipped_count = 0
    processed_sheet_names: list[str] = []
    results: list[SyncRecipeSheetResponse] = []

    for sheet_name in available_sheets:
        previous_sync = synced_sheets.get(sheet_name)
        if previous_sync and not force:
            skipped_count += 1
            results.append(SyncRecipeSheetResponse(
                sheet_name=sheet_name,
                status="skipped",
                recipe_id=UUID(previous_sync["recipe_id"]) if previous_sync.get("recipe_id") else None,
                recipe_name=previous_sync.get("recipe_name"),
                message="Hoja ya sincronizada",
            ))
            continue

        recipe_id, was_new = upsert_recipe_from_import(doc, db, sheet_override=sheet_name)
        if not recipe_id:
            results.append(SyncRecipeSheetResponse(
                sheet_name=sheet_name,
                status="error",
                message="No se pudo extraer una receta valida de esta hoja.",
            ))
            continue

        recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
        doc.synced_recipe_id = recipe_id
        crud.add_log(db, doc.id, "SYNC_PRODUCTION", user_id, {
            "recipe_id": str(recipe_id),
            "recipe_name": recipe.name if recipe else None,
            "sheet_used": sheet_name,
            "was_new": was_new,
            "batch": True,
        })

        processed_count += 1
        processed_sheet_names.append(sheet_name)
        results.append(SyncRecipeSheetResponse(
            sheet_name=sheet_name,
            status="created" if was_new else "updated",
            recipe_id=recipe_id,
            recipe_name=recipe.name if recipe else sheet_name,
            was_new=was_new,
            total_cost=float(recipe.total_cost) if recipe and recipe.total_cost else 0.0,
            ingredients_count=len(recipe.ingredients) if recipe else 0,
        ))

    crud.add_log(db, doc.id, "SYNC_PRODUCTION_BATCH", user_id, {
        "processed_count": processed_count,
        "skipped_count": skipped_count,
        "sheet_count": len(available_sheets),
        "sheets": processed_sheet_names,
        "force": force,
    })
    db.commit()

    return SyncRecipesResponse(
        total_sheets=len(available_sheets),
        processed_count=processed_count,
        skipped_count=skipped_count,
        results=results,
    )


@router.patch("/documents/{doc_id}/edit", response_model=DocumentoOut, dependencies=protected)
def edit_document_fields(doc_id: UUID, body: EditFieldsRequest, request: Request, db: Session = Depends(get_db)):
    user_id = _user_id(request)
    doc = crud.get_documento(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    # Merge with existing extracted data
    current = doc.datos_extraidos or {}
    if isinstance(current, dict):
        previous = {k: current.get(k) for k in body.campos}
        current.update(body.campos)

    crud.update_documento(db, doc, {"datos_extraidos": current})
    crud.add_log(db, doc.id, "EDIT", user_id, {"campos_modificados": body.campos, "valores_anteriores": previous})
    db.commit()
    return doc


@router.post("/documents/{doc_id}/reject", response_model=DocumentoOut, dependencies=protected)
def reject_document(doc_id: UUID, request: Request, db: Session = Depends(get_db)):
    user_id = _user_id(request)
    doc = crud.get_documento(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    crud.update_documento(db, doc, {"estado": "FAILED"})
    crud.add_log(db, doc.id, "REJECT", user_id)
    db.commit()
    return doc


@router.get("/documents/{doc_id}/logs", response_model=list[LogCambioOut], dependencies=protected)
def get_document_logs(doc_id: UUID, request: Request, db: Session = Depends(get_db)):
    return crud.get_logs(db, doc_id)


@router.get("/dashboard", response_model=DashboardStats, dependencies=protected)
def get_dashboard(request: Request, db: Session = Depends(get_db)):
    tenant_id = _tenant_id(request)
    counts = crud.count_documentos(db, tenant_id)
    return DashboardStats(
        total=sum(counts.values()),
        pendientes=counts.get("PENDING", 0) + counts.get("PROCESSING", 0),
        en_revision=counts.get("REVIEW", 0),
        confirmados=counts.get("CONFIRMED", 0),
        fallidos=counts.get("FAILED", 0),
    )


def _safe_float(val) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
