"""Document Storage API — WORM + SHA256 dedupe."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from app.modules.documents.application.document_storage_service import DocumentStorageService
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/documents/storage",
    tags=["documents-storage"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


def _tenant_id_from_request(request: Request) -> UUID:
    claims = getattr(request.state, "access_claims", None)
    if not isinstance(claims, dict):
        raise HTTPException(status_code=401, detail="access_claims_missing")
    tid = claims.get("tenant_id")
    if not tid:
        raise HTTPException(status_code=400, detail="tenant_id_missing")
    return UUID(str(tid))


@router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    doc_type: str = Form(default="unknown"),
    source: str = Form(default="upload"),
    db: Session = Depends(get_db),
):
    """Upload a document with SHA256 deduplication."""
    tenant_id = _tenant_id_from_request(request)

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    svc = DocumentStorageService(db)
    doc, version, is_duplicate = svc.upload_document(
        tenant_id=tenant_id,
        created_by=tenant_id,
        file_content=content,
        file_name=file.filename or "unnamed",
        mime=file.content_type or "application/octet-stream",
        source=source,
        doc_type=doc_type,
    )

    db.commit()

    if not is_duplicate:
        try:
            AuditService.log_action(
                db=db,
                action_type="CREATE",
                entity_type="document_version",
                entity_id=str(version.id),
                tenant_id=tenant_id,
                new_data={
                    "file_name": version.file_name,
                    "sha256": version.sha256,
                    "size": version.size,
                },
                description=f"Document uploaded: {version.file_name}",
            )
        except Exception:
            logger.debug("Audit log failed for document upload", exc_info=True)

    return {
        "document_id": str(doc.id),
        "version_id": str(version.id),
        "version": version.version,
        "sha256": version.sha256,
        "is_duplicate": is_duplicate,
        "file_name": version.file_name,
        "size": version.size,
    }


@router.get("")
def list_documents(
    request: Request,
    doc_type: str | None = Query(None),
    status: str = Query("active"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id_from_request(request)

    svc = DocumentStorageService(db)
    docs = svc.list_documents(
        tenant_id=tenant_id,
        doc_type=doc_type,
        status=status,
        limit=limit,
        offset=offset,
    )
    return [
        {
            "id": str(d.id),
            "doc_type": d.doc_type,
            "source": d.source,
            "status": d.status,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in docs
    ]


@router.get("/{document_id}")
def get_document(
    document_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id_from_request(request)

    svc = DocumentStorageService(db)
    doc = svc.get_document(tenant_id=tenant_id, document_id=document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    versions = svc.get_versions(tenant_id=tenant_id, document_id=document_id)
    return {
        "id": str(doc.id),
        "doc_type": doc.doc_type,
        "source": doc.source,
        "status": doc.status,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "versions": [
            {
                "id": str(v.id),
                "version": v.version,
                "file_name": v.file_name,
                "mime": v.mime,
                "size": v.size,
                "sha256": v.sha256,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ],
    }
