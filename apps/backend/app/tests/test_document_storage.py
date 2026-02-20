"""Tests for Document Storage Service — WORM + SHA256 dedupe"""

import uuid

# Register models with Base
import app.models.core.document_storage  # noqa: F401


class TestDocumentStorageService:
    """Test DocumentStorageService"""

    def _make_tenant(self, db):
        from app.models.tenant import Tenant

        tid = uuid.uuid4()
        t = Tenant(id=tid, name="Doc Test", slug=f"doc-{tid.hex[:8]}")
        db.add(t)
        db.flush()
        return tid

    def _svc(self, db):
        from app.modules.documents.application.document_storage_service import (
            DocumentStorageService,
        )

        return DocumentStorageService(db)

    def test_upload_creates_document_and_version(self, db):
        tid = self._make_tenant(db)
        svc = self._svc(db)
        content = b"hello world document"
        doc, ver, is_dup = svc.upload_document(
            tenant_id=tid,
            created_by=tid,
            file_content=content,
            file_name="test.pdf",
            mime="application/pdf",
            source="upload",
            doc_type="invoice_vendor",
        )
        db.flush()
        assert doc is not None
        assert ver is not None
        assert is_dup is False
        assert ver.version == 1
        assert ver.file_name == "test.pdf"
        assert ver.size == len(content)
        assert len(ver.sha256) == 64

    def test_upload_duplicate_returns_existing(self, db):
        tid = self._make_tenant(db)
        svc = self._svc(db)
        content = b"duplicate content"
        doc1, ver1, dup1 = svc.upload_document(
            tenant_id=tid,
            created_by=tid,
            file_content=content,
            file_name="a.pdf",
            mime="application/pdf",
        )
        db.flush()
        doc2, ver2, dup2 = svc.upload_document(
            tenant_id=tid,
            created_by=tid,
            file_content=content,
            file_name="b.pdf",
            mime="application/pdf",
        )
        assert dup1 is False
        assert dup2 is True
        assert str(ver1.id) == str(ver2.id)

    def test_different_content_creates_separate_docs(self, db):
        tid = self._make_tenant(db)
        svc = self._svc(db)
        _, ver1, _ = svc.upload_document(
            tenant_id=tid,
            created_by=tid,
            file_content=b"content A",
            file_name="a.pdf",
            mime="application/pdf",
        )
        _, ver2, _ = svc.upload_document(
            tenant_id=tid,
            created_by=tid,
            file_content=b"content B",
            file_name="b.pdf",
            mime="application/pdf",
        )
        db.flush()
        assert ver1.sha256 != ver2.sha256

    def test_get_document(self, db):
        tid = self._make_tenant(db)
        svc = self._svc(db)
        doc, _, _ = svc.upload_document(
            tenant_id=tid,
            created_by=tid,
            file_content=b"get me",
            file_name="get.txt",
            mime="text/plain",
        )
        db.flush()
        found = svc.get_document(tid, doc.id)
        assert found is not None
        assert str(found.id) == str(doc.id)

    def test_get_document_wrong_tenant_returns_none(self, db):
        tid1 = self._make_tenant(db)
        tid2 = self._make_tenant(db)
        svc = self._svc(db)
        doc, _, _ = svc.upload_document(
            tenant_id=tid1,
            created_by=tid1,
            file_content=b"tenant1 doc",
            file_name="t1.pdf",
            mime="application/pdf",
        )
        db.flush()
        assert svc.get_document(tid2, doc.id) is None

    def test_list_documents(self, db):
        tid = self._make_tenant(db)
        svc = self._svc(db)
        for i in range(3):
            svc.upload_document(
                tenant_id=tid,
                created_by=tid,
                file_content=f"doc {i}".encode(),
                file_name=f"doc{i}.pdf",
                mime="application/pdf",
                doc_type="sales_excel",
            )
        db.flush()
        docs = svc.list_documents(tid, doc_type="sales_excel")
        assert len(docs) == 3

    def test_list_documents_with_limit(self, db):
        tid = self._make_tenant(db)
        svc = self._svc(db)
        for i in range(5):
            svc.upload_document(
                tenant_id=tid,
                created_by=tid,
                file_content=f"limited {i}".encode(),
                file_name=f"lim{i}.pdf",
                mime="application/pdf",
            )
        db.flush()
        docs = svc.list_documents(tid, limit=2)
        assert len(docs) == 2

    def test_get_versions(self, db):
        tid = self._make_tenant(db)
        svc = self._svc(db)
        doc, ver1, _ = svc.upload_document(
            tenant_id=tid,
            created_by=tid,
            file_content=b"v1 content",
            file_name="versioned.pdf",
            mime="application/pdf",
        )
        db.flush()
        versions = svc.get_versions(tid, doc.id)
        assert len(versions) == 1
        assert versions[0].version == 1

    def test_add_version_increments(self, db):
        tid = self._make_tenant(db)
        svc = self._svc(db)
        doc, ver1, _ = svc.upload_document(
            tenant_id=tid,
            created_by=tid,
            file_content=b"original",
            file_name="ver.pdf",
            mime="application/pdf",
        )
        db.flush()
        ver2, is_dup = svc.add_version(
            tenant_id=tid,
            document_id=doc.id,
            file_content=b"updated content",
            file_name="ver_v2.pdf",
            mime="application/pdf",
        )
        db.flush()
        assert is_dup is False
        assert ver2.version == 2

    def test_add_version_duplicate_skips(self, db):
        tid = self._make_tenant(db)
        svc = self._svc(db)
        doc, _, _ = svc.upload_document(
            tenant_id=tid,
            created_by=tid,
            file_content=b"same content",
            file_name="dup.pdf",
            mime="application/pdf",
        )
        db.flush()
        ver2, is_dup = svc.add_version(
            tenant_id=tid,
            document_id=doc.id,
            file_content=b"same content",
            file_name="dup_v2.pdf",
            mime="application/pdf",
        )
        assert is_dup is True
