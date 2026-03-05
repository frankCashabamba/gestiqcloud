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
import hashlib
import datetime
from .schemas import (
    ConfirmRequest, DashboardStats, DocumentoDetailOut, DocumentoListOut,
    DocumentoOut, EditFieldsRequest, LogCambioOut, UploadResponse,
)

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

            # Auto-resolver de receta si no viene receta (upload no permite recipe_id)
            recipe_config, resolved_snapshot_id, resolution_mode, _, _ = resolve_auto_recipe(
                db, tenant_id, sheet_profiles or {}, user_id,
            )

            # Preparar contenido para el LLM
            has_structured = bool(structured and isinstance(structured, list) and sheet_profiles)
            if has_structured:
                # headers_norm = claves normalizadas que usan los dicts de filas ("precio_unitario_venta")
                # headers_display = nombres legibles ("PRECIO UNITARIO VENTA") para enviar al LLM y mostrar en UI
                headers_norm: list[str] = []
                headers_display: list[str] = []
                for prof in sheet_profiles.values():
                    headers_norm = prof.get("headers_norm") or []
                    headers_display = prof.get("headers") or headers_norm
                    break
                headers = headers_norm
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
                recipe_config=recipe_config,
            )

            tipo_doc = analysis.get("tipo_documento", "OTRO")
            confianza = float(analysis.get("confianza", 0.0))
            requiere_revision = confianza < CONFIDENCE_THRESHOLD
            es_tabla = analysis.get("es_tabla", False)

            crud.add_log(db, doc.id, "CLASSIFY", user_id, {
                "tipo_documento": tipo_doc, "confianza": confianza,
                "razonamiento": analysis.get("razonamiento", ""), "model_used": analysis.get("model_used"),
            })

            # Construir datos_extraidos
            if es_tabla and has_structured:
                # Tabla: usar filas ya parseadas (structured_data); no se pide al LLM que reprocese filas
                # columnas = display names para la UI; columnas_norm = claves reales de los dicts de filas
                columnas = headers_display or headers_norm
                datos_extraidos = {
                    "filas": structured[:200],
                    "total_filas": len(structured),
                    "columnas": columnas,
                    "columnas_norm": headers_norm,
                }
            else:
                # Documento único o tabla extraída por LLM desde texto (PDF, etc.)
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
    doc = crud.get_documento(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return doc


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
