from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy.orm import Session

from app.models.core.modelsimport import ImportBatch, ImportItem


class ImportsRepository:
    """Minimal repository interface (to be implemented with SQLAlchemy models).

    All methods must be scoped by empresa_id externally or via filters.
    """

    # Batches
    def get_batch(self, db: Session, empresa_id: int, batch_id) -> Optional[ImportBatch]:
        return (
            db.query(ImportBatch)
            .filter(ImportBatch.id == batch_id, ImportBatch.empresa_id == empresa_id)
            .first()
        )

    def list_batches(self, db: Session, empresa_id: int, *, status: Optional[str] = None) -> List[ImportBatch]:
        q = db.query(ImportBatch).filter(ImportBatch.empresa_id == empresa_id)
        if status:
            q = q.filter(ImportBatch.status == status)
        return q.order_by(ImportBatch.created_at.desc()).all()

    # Items
    def list_items(
        self,
        db: Session,
        empresa_id: int,
        batch_id,
        *,
        status: Optional[str] = None,
        q: Optional[str] = None,
    ) -> List[ImportItem]:
        # empresa_id is enforced by joining batch
        query = (
            db.query(ImportItem)
            .join(ImportBatch, ImportItem.batch_id == ImportBatch.id)
            .filter(ImportBatch.id == batch_id, ImportBatch.empresa_id == empresa_id)
        )
        if status:
            query = query.filter(ImportItem.status == status)
        # naive q filter over normalized JSON as text via CAST; tune with PG JSONB ops if needed
        if q:
            from sqlalchemy import cast, String

            query = query.filter(cast(ImportItem.normalized, String).ilike(f"%{q}%"))
        return query.order_by(ImportItem.idx.asc()).all()

    def bulk_add_items(self, db: Session, empresa_id: int, batch_id, items: Iterable[Dict[str, Any]]) -> int:
        """Insert items skipping duplicates by (batch_id, idempotency_key) when present.

        This provides idempotent ingestion without requiring a DB unique index.
        """
        # Preload existing idempotency keys for the batch
        existing_keys = set(
            k for (k,) in (
                db.query(ImportItem.idempotency_key)
                .filter(ImportItem.batch_id == batch_id)
                .all()
            ) if k is not None
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

    def exists_promoted_hash(self, db: Session, empresa_id: int, dedupe_hash: str) -> bool:
        q = (
            db.query(ImportItem)
            .join(ImportBatch, ImportItem.batch_id == ImportBatch.id)
            .filter(
                ImportBatch.empresa_id == empresa_id,
                ImportItem.dedupe_hash == dedupe_hash,
                ImportItem.status == "PROMOTED",
            )
        )
        return db.query(q.exists()).scalar() or False
