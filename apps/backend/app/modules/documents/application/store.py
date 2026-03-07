from __future__ import annotations

from threading import Lock

from app.modules.documents.domain.models import DocumentModel


class DocumentStore:
    """In-memory store for MVP. Replace with DB persistence."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._docs: dict[str, DocumentModel] = {}

    def put(self, doc: DocumentModel) -> None:
        with self._lock:
            self._docs[doc.document.id] = doc

    def get(self, doc_id: str) -> DocumentModel | None:
        with self._lock:
            return self._docs.get(doc_id)

    def list_for_tenant(self, tenant_id: str, doc_type: str | None = None) -> list[DocumentModel]:
        with self._lock:
            result = [d for d in self._docs.values() if d.seller.tenantId == tenant_id]
            if doc_type:
                result = [d for d in result if d.document.type == doc_type]
            return result


store = DocumentStore()
