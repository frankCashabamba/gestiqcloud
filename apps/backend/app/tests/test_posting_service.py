"""Tests for PostingService — idempotency + import resolutions"""
import uuid

import pytest

import app.models.core.modelsimport  # noqa: F401


class TestPostingService:
    """Test PostingService idempotency"""

    def _make_tenant(self, db):
        from app.models.tenant import Tenant
        tid = uuid.uuid4()
        t = Tenant(id=tid, name="Post Test", slug=f"post-{tid.hex[:8]}")
        db.add(t)
        db.flush()
        return tid

    def _make_batch(self, db, tenant_id):
        from app.models.core.modelsimport import ImportBatch
        batch = ImportBatch(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            source_type="invoices",
            origin="api",
            created_by="test",
        )
        db.add(batch)
        db.flush()
        return batch.id

    def _svc(self, db):
        from app.modules.imports.services.posting_service import PostingService
        return PostingService(db)

    def test_compute_posting_key_deterministic(self, db):
        tid = self._make_tenant(db)
        batch_id = self._make_batch(db, tid)
        svc = self._svc(db)
        data = {"invoice_number": "INV-001", "vendor_name": "Acme", "total": "100.00"}
        key1 = svc.compute_posting_key(tid, batch_id, "invoice", data)
        key2 = svc.compute_posting_key(tid, batch_id, "invoice", data)
        assert key1 == key2
        assert len(key1) == 64  # SHA256 hex

    def test_compute_posting_key_different_data(self, db):
        tid = self._make_tenant(db)
        batch_id = self._make_batch(db, tid)
        svc = self._svc(db)
        key1 = svc.compute_posting_key(tid, batch_id, "invoice", {"invoice_number": "A"})
        key2 = svc.compute_posting_key(tid, batch_id, "invoice", {"invoice_number": "B"})
        assert key1 != key2

    def test_check_and_register_new(self, db):
        tid = self._make_tenant(db)
        batch_id = self._make_batch(db, tid)
        svc = self._svc(db)
        key = svc.compute_posting_key(tid, batch_id, "invoice", {"invoice_number": "X"})
        is_dup, record = svc.check_and_register(tid, batch_id, key, "invoice")
        db.flush()
        assert is_dup is False
        assert record is not None
        assert record.posting_key == key

    def test_check_and_register_duplicate(self, db):
        tid = self._make_tenant(db)
        batch_id = self._make_batch(db, tid)
        svc = self._svc(db)
        key = svc.compute_posting_key(tid, batch_id, "invoice", {"invoice_number": "DUP"})
        is_dup1, _ = svc.check_and_register(tid, batch_id, key, "invoice", entity_id=uuid.uuid4())
        db.flush()
        is_dup2, existing = svc.check_and_register(tid, batch_id, key, "invoice")
        assert is_dup1 is False
        assert is_dup2 is True
        assert existing.entity_type == "invoice"

    def test_is_duplicate(self, db):
        tid = self._make_tenant(db)
        batch_id = self._make_batch(db, tid)
        svc = self._svc(db)
        key = "test-key-abc123"
        assert svc.is_duplicate(tid, key) is False
        svc.check_and_register(tid, batch_id, key, "product")
        db.flush()
        assert svc.is_duplicate(tid, key) is True

    def test_different_tenants_same_key(self, db):
        tid1 = self._make_tenant(db)
        tid2 = self._make_tenant(db)
        batch1 = self._make_batch(db, tid1)
        batch2 = self._make_batch(db, tid2)
        svc = self._svc(db)
        key = "shared-posting-key"
        dup1, _ = svc.check_and_register(tid1, batch1, key, "invoice")
        db.flush()
        dup2, _ = svc.check_and_register(tid2, batch2, key, "invoice")
        db.flush()
        # Different tenants should NOT conflict
        assert dup1 is False
        assert dup2 is False


class TestImportResolutions:
    """Test import resolution persistence"""

    def _make_tenant(self, db):
        from app.models.tenant import Tenant
        tid = uuid.uuid4()
        t = Tenant(id=tid, name="Res Test", slug=f"res-{tid.hex[:8]}")
        db.add(t)
        db.flush()
        return tid

    def _make_batch(self, db, tenant_id):
        from app.models.core.modelsimport import ImportBatch
        batch = ImportBatch(
            id=uuid.uuid4(), tenant_id=tenant_id,
            source_type="invoices", origin="api", created_by="test",
        )
        db.add(batch)
        db.flush()
        return batch.id

    def _svc(self, db):
        from app.modules.imports.services.posting_service import PostingService
        return PostingService(db)

    def test_save_resolution_creates(self, db):
        tid = self._make_tenant(db)
        batch_id = self._make_batch(db, tid)
        svc = self._svc(db)
        res = svc.save_resolution(
            tenant_id=tid, import_job_id=batch_id,
            entity_type="product", raw_value="PAN TAPADO",
            resolved_id=uuid.uuid4(), status="resolved",
            confidence=0.95, resolved_by="ai",
        )
        db.flush()
        assert res is not None
        assert res.raw_value == "PAN TAPADO"
        assert res.status == "resolved"
        assert float(res.confidence) == 0.95

    def test_save_resolution_updates_existing(self, db):
        tid = self._make_tenant(db)
        batch_id = self._make_batch(db, tid)
        svc = self._svc(db)
        resolved_id = uuid.uuid4()
        svc.save_resolution(
            tenant_id=tid, import_job_id=batch_id,
            entity_type="product", raw_value="BAGUETTE",
            status="pending",
        )
        db.flush()
        res = svc.save_resolution(
            tenant_id=tid, import_job_id=batch_id,
            entity_type="product", raw_value="BAGUETTE",
            resolved_id=resolved_id, status="resolved",
            confidence=0.88, resolved_by="manual",
        )
        db.flush()
        assert str(res.resolved_id) == str(resolved_id)
        assert res.status == "resolved"

    def test_get_resolutions(self, db):
        tid = self._make_tenant(db)
        batch_id = self._make_batch(db, tid)
        svc = self._svc(db)
        svc.save_resolution(tid, batch_id, "product", "Item A")
        svc.save_resolution(tid, batch_id, "supplier", "Proveedor X")
        db.flush()
        results = svc.get_resolutions(tid, batch_id)
        assert len(results) == 2

    def test_find_previous_resolution(self, db):
        tid = self._make_tenant(db)
        batch_id = self._make_batch(db, tid)
        svc = self._svc(db)
        resolved_id = uuid.uuid4()
        svc.save_resolution(
            tid, batch_id, "product", "CROISSANT",
            resolved_id=resolved_id, status="resolved",
        )
        db.flush()
        prev = svc.find_previous_resolution(tid, "product", "CROISSANT")
        assert prev is not None
        assert str(prev.resolved_id) == str(resolved_id)

    def test_find_previous_resolution_none_when_pending(self, db):
        tid = self._make_tenant(db)
        batch_id = self._make_batch(db, tid)
        svc = self._svc(db)
        svc.save_resolution(tid, batch_id, "product", "MUFFIN", status="pending")
        db.flush()
        prev = svc.find_previous_resolution(tid, "product", "MUFFIN")
        assert prev is None
