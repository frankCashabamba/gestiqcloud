from __future__ import annotations

import logging
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.core.document import Document
from app.modules.documents.domain.models import DocumentModel

_log = logging.getLogger(__name__)


def _resolve_tenant_uuid(db: Session, tenant_id: str) -> uuid.UUID:
    """Convierte tenant_id (UUID string o numérico) a uuid.UUID."""
    try:
        return uuid.UUID(str(tenant_id))
    except (ValueError, AttributeError):
        pass
    # Fallback: leer el UUID ya resuelto en la sesión (set por get_db)
    resolved = db.info.get("tenant_id") if hasattr(db, "info") else None
    if resolved:
        try:
            return uuid.UUID(str(resolved))
        except (ValueError, AttributeError):
            pass
    # Último recurso: buscar en DB por id numérico
    if str(tenant_id).isdigit():
        row = db.execute(
            text("SELECT id FROM tenants WHERE tenant_id = :eid"),
            {"eid": int(tenant_id)},
        ).first()
        if row:
            return uuid.UUID(str(row[0]))
    raise ValueError(f"No se pudo resolver tenant_id={tenant_id!r} a UUID")


def save_document(
    db: Session,
    *,
    tenant_id: str,
    doc: DocumentModel,
    config_version: int | None,
    effective_from: str | None,
    country_pack_version: str | None,
) -> None:
    tenant_uuid = _resolve_tenant_uuid(db, tenant_id)
    record = Document(
        id=uuid.UUID(doc.document.id),
        tenant_id=tenant_uuid,
        doc_type=doc.document.type,
        status=doc.document.status,
        country=doc.document.country,
        issued_at=doc.document.issuedAt,
        series=doc.document.series,
        sequential=doc.document.sequential,
        currency=doc.document.currency,
        template_id=doc.render.templateId,
        template_version=doc.render.templateVersion,
        config_version=config_version,
        config_effective_from=effective_from,
        country_pack_version=country_pack_version,
        payload=doc.model_dump(mode="json"),
    )
    db.add(record)
    db.commit()
    _log.info("SAVE_DOC_OK id=%s status=%s", record.id, record.status)


def get_document(db: Session, document_id: str) -> DocumentModel | None:
    try:
        doc_key = uuid.UUID(document_id) if isinstance(document_id, str) else document_id
    except Exception:
        doc_key = document_id
    row = db.get(Document, doc_key)
    if not row:
        return None
    return DocumentModel(**row.payload)
