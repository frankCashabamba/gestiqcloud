from __future__ import annotations

import uuid
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy.orm import Session

from app.models.core.modelsimport import ImportBatch, ImportItem
from .tenant_middleware import with_tenant_context


class ImportsRepository:
    """Repository for imports module with RLS tenant isolation.

    All methods expect tenant_id (UUID) as first parameter.
    RLS policies enforce tenant isolation at DB level.
    """

    # Batches
    @with_tenant_context
    def get_batch(
        self, db: Session, tenant_id: uuid.UUID, batch_id: int
    ) -> Optional[ImportBatch]:
        # RLS handles tenant_id filtering
        return db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()

    @with_tenant_context
    def list_batches(
        self,
        db: Session,
        tenant_id: uuid.UUID,
        *,
        status: Optional[str] = None,
    ) -> List[ImportBatch]:
        # RLS handles tenant_id filtering
        q = db.query(ImportBatch)
        if status:
            q = q.filter(ImportBatch.status == status)
        return q.order_by(ImportBatch.created_at.desc()).all()

    # Items
    @with_tenant_context
    def list_items(
        self,
        db: Session,
        tenant_id: uuid.UUID,
        batch_id: int,
        *,
        status: Optional[str] = None,
        q: Optional[str] = None,
    ) -> List[ImportItem]:
        # RLS handles tenant_id filtering via batch join
        query = (
            db.query(ImportItem)
            .join(ImportBatch, ImportItem.batch_id == ImportBatch.id)
            .filter(ImportBatch.id == batch_id)
        )
        if status:
            query = query.filter(ImportItem.status == status)
        if q:
            from sqlalchemy import cast, String
            query = query.filter(cast(ImportItem.normalized, String).ilike(f"%{q}%"))
        return query.order_by(ImportItem.idx.asc()).all()

    @with_tenant_context
    def bulk_add_items(
        self,
        db: Session,
        tenant_id: uuid.UUID,
        batch_id: int,
        items: Iterable[Dict[str, Any]],
    ) -> int:
        """Insert items skipping duplicates by (batch_id, idempotency_key)."""
        # RLS ensures only tenant's items are queried
        existing_keys = set(
            k
            for (k,) in db.query(ImportItem.idempotency_key)
            .filter(ImportItem.batch_id == batch_id)
            .all()
            if k is not None
        )
        count = 0
        for data in items:
            idem = data.get("idempotency_key")
            if idem and idem in existing_keys:
                continue
            obj = ImportItem(batch_id=batch_id, **data)
            db.add(obj)
            if idem:
                existing_keys.add(idem)
            count += 1
        db.commit()
        return count

    @with_tenant_context
    def exists_promoted_hash(
        self, db: Session, tenant_id: uuid.UUID, dedupe_hash: str
    ) -> bool:
        # RLS handles tenant_id filtering
        q = db.query(ImportItem).join(ImportBatch).filter(
            ImportItem.dedupe_hash == dedupe_hash,
            ImportItem.status == "PROMOTED",
        )
        return db.query(q.exists()).scalar() or False
