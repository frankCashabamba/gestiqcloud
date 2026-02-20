"""Document Storage Service — WORM + SHA256 dedupe."""

from __future__ import annotations

import hashlib
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.core.document_storage import DocumentFile, DocumentVersion


class DocumentStorageService:
    def __init__(self, db: Session):
        self.db = db

    def upload_document(
        self,
        tenant_id: UUID,
        created_by: UUID,
        file_content: bytes,
        file_name: str,
        mime: str,
        source: str = "upload",
        doc_type: str = "unknown",
        storage_uri: str | None = None,
        tags: dict | None = None,
    ) -> tuple[DocumentFile, DocumentVersion, bool]:
        """Upload a document with SHA256 dedupe.

        Returns (doc, version, is_duplicate).
        If sha256 already exists for tenant, returns existing without creating new.
        """
        sha256_hash = hashlib.sha256(file_content).hexdigest()

        existing = (
            self.db.query(DocumentVersion)
            .filter(
                DocumentVersion.tenant_id == tenant_id,
                DocumentVersion.sha256 == sha256_hash,
            )
            .first()
        )

        if existing:
            doc = (
                self.db.query(DocumentFile).filter(DocumentFile.id == existing.document_id).first()
            )
            return doc, existing, True

        doc = DocumentFile(
            tenant_id=tenant_id,
            created_by=created_by,
            source=source,
            doc_type=doc_type,
            status="active",
            tags=tags,
        )
        self.db.add(doc)
        self.db.flush()

        version = DocumentVersion(
            tenant_id=tenant_id,
            document_id=doc.id,
            version=1,
            file_name=file_name,
            mime=mime,
            size=len(file_content),
            sha256=sha256_hash,
            storage_uri=storage_uri or f"uploads/{tenant_id}/{doc.id}/{file_name}",
        )
        self.db.add(version)
        self.db.flush()

        return doc, version, False

    def get_document(self, tenant_id: UUID, document_id: UUID) -> DocumentFile | None:
        return (
            self.db.query(DocumentFile)
            .filter(
                DocumentFile.tenant_id == tenant_id,
                DocumentFile.id == document_id,
            )
            .first()
        )

    def list_documents(
        self,
        tenant_id: UUID,
        doc_type: str | None = None,
        status: str = "active",
        limit: int = 50,
        offset: int = 0,
    ) -> list[DocumentFile]:
        q = self.db.query(DocumentFile).filter(
            DocumentFile.tenant_id == tenant_id,
            DocumentFile.status == status,
        )
        if doc_type:
            q = q.filter(DocumentFile.doc_type == doc_type)
        return q.order_by(DocumentFile.created_at.desc()).offset(offset).limit(limit).all()

    def get_versions(self, tenant_id: UUID, document_id: UUID) -> list[DocumentVersion]:
        return (
            self.db.query(DocumentVersion)
            .filter(
                DocumentVersion.tenant_id == tenant_id,
                DocumentVersion.document_id == document_id,
            )
            .order_by(DocumentVersion.version.desc())
            .all()
        )

    def add_version(
        self,
        tenant_id: UUID,
        document_id: UUID,
        file_content: bytes,
        file_name: str,
        mime: str,
        storage_uri: str | None = None,
    ) -> tuple[DocumentVersion, bool]:
        sha256_hash = hashlib.sha256(file_content).hexdigest()

        existing = (
            self.db.query(DocumentVersion)
            .filter(
                DocumentVersion.tenant_id == tenant_id,
                DocumentVersion.sha256 == sha256_hash,
            )
            .first()
        )

        if existing:
            return existing, True

        max_version = (
            self.db.query(func.max(DocumentVersion.version))
            .filter(DocumentVersion.document_id == document_id)
            .scalar()
            or 0
        )

        version = DocumentVersion(
            tenant_id=tenant_id,
            document_id=document_id,
            version=max_version + 1,
            file_name=file_name,
            mime=mime,
            size=len(file_content),
            sha256=sha256_hash,
            storage_uri=storage_uri or f"uploads/{tenant_id}/{document_id}/{file_name}",
        )
        self.db.add(version)
        self.db.flush()
        return version, False
