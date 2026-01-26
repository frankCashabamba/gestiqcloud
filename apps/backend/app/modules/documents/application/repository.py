from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.core.document import Document
from app.modules.documents.application.store import store
from app.modules.documents.domain.models import DocumentModel


def save_document(
    db: Session,
    *,
    tenant_id: str,
    doc: DocumentModel,
    config_version: int | None,
    effective_from: str | None,
    country_pack_version: str | None,
) -> None:
    try:
        record = Document(
            id=doc.document.id,
            tenant_id=tenant_id,
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
            payload=doc.model_dump(),
        )
        db.add(record)
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        store.put(doc)


def get_document(db: Session, document_id: str) -> DocumentModel | None:
    try:
        doc_key = document_id
        try:
            if isinstance(document_id, str):
                doc_key = uuid.UUID(document_id)
        except Exception:
            doc_key = document_id
        row = db.get(Document, doc_key)
        if not row:
            return store.get(str(document_id))
        return DocumentModel(**row.payload)
    except Exception:
        return store.get(str(document_id))
