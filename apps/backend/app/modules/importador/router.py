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
from .ai_classifier import CONFIDENCE_THRESHOLD, classify_document, extract_fields
from .ocr_service import detect_file_type, extract_text_from_file
from .schemas import (
    ConfirmRequest, DashboardStats, DocumentoDetailOut, DocumentoListOut,
    DocumentoOut, EditFieldsRequest, LogCambioOut, UploadResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/importador", tags=["Importador"])
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


@router.post("/upload", response_model=list[UploadResponse], dependencies=protected)
async def upload_files(
    request: Request,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """Upload one or multiple files. Auto-classifies and extracts data."""
    tenant_id = _tenant_id(request)
    user_id = _user_id(request)
    results = []

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
        })
        crud.add_log(db, doc.id, "UPLOAD", user_id, {"filename": filename, "size": len(file_bytes)})
        db.commit()

        try:
            # 1. Extract text/data
            extraction = await extract_text_from_file(file_bytes, filename)
            text = extraction.get("text", "")
            structured = extraction.get("structured_data")

            # 2. Classify
            classification = await classify_document(text, filename, extraction.get("format", ""))
            tipo_doc = classification.get("tipo_documento", "OTRO")
            confianza = float(classification.get("confianza", 0.0))
            requiere_revision = confianza < CONFIDENCE_THRESHOLD

            crud.add_log(db, doc.id, "CLASSIFY", user_id, classification)

            # 3. Extract fields
            if structured and tipo_archivo in ("XLSX", "XLS", "CSV"):
                datos_extraidos = {"filas": structured[:100], "total_filas": len(structured)} if structured else {}
            else:
                datos_extraidos = await extract_fields(text, tipo_doc, filename)

            crud.add_log(db, doc.id, "EXTRACT", user_id, {"campos_extraidos": list(datos_extraidos.keys()) if isinstance(datos_extraidos, dict) else []})

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
