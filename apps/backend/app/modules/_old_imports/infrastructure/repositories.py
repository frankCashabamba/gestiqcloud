from __future__ import annotations

import uuid
from collections.abc import Iterable
from typing import Any

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
    def get_batch(self, db: Session, tenant_id: uuid.UUID, batch_id: int) -> ImportBatch | None:
        # RLS handles tenant_id filtering
        return db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()

    @with_tenant_context
    def list_batches(
        self,
        db: Session,
        tenant_id: uuid.UUID,
        *,
        status: str | None = None,
    ) -> list[ImportBatch]:
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
        status: str | None = None,
        q: str | None = None,
    ) -> list[ImportItem]:
        # RLS handles tenant_id filtering via batch join
        query = (
            db.query(ImportItem)
            .join(ImportBatch, ImportItem.batch_id == ImportBatch.id)
            .filter(ImportBatch.id == batch_id)
        )
        if status:
            query = query.filter(ImportItem.status == status)
        if q:
            from sqlalchemy import String, cast

            query = query.filter(cast(ImportItem.normalized, String).ilike(f"%{q}%"))
        return query.order_by(ImportItem.idx.asc()).all()

    @with_tenant_context
    def bulk_add_items(
        self,
        db: Session,
        tenant_id: uuid.UUID,
        batch_id: int,
        items: Iterable[dict[str, Any]],
    ) -> int:
        """Insert items skipping duplicates by (batch_id, idempotency_key)."""
        items_list = list(items)
        print(
            f"DEBUG bulk_add_items: tenant_id={tenant_id}, batch_id={batch_id}, items count={len(items_list)}"
        )
        if not items_list:
            return 0

        # Add batch_id and tenant_id to each item
        for item in items_list:
            item["batch_id"] = batch_id
            item["tenant_id"] = tenant_id
            if "id" not in item:
                item["id"] = uuid.uuid4()

        print(f"DEBUG: First item sample: {items_list[0]}")
        bind = db.get_bind()
        dialect = getattr(bind, "dialect", None)
        dialect_name = getattr(dialect, "name", "")
        dialect_name = dialect_name.lower() if isinstance(dialect_name, str) else ""
        if dialect_name == "sqlite":
            from sqlalchemy import insert as sa_insert

            stmt = sa_insert(ImportItem).values(items_list).prefix_with("OR IGNORE")
        else:
            from sqlalchemy.dialects.postgresql import insert as pg_insert

            stmt = pg_insert(ImportItem).values(items_list)
            stmt = stmt.on_conflict_do_nothing(
                index_elements=[ImportItem.tenant_id, ImportItem.idempotency_key]
            )

        result = db.execute(stmt)
        print(f"DEBUG: Execute result rowcount={result.rowcount}")
        db.flush()  # Flush instead of commit, let caller commit

        # Return number of rows actually inserted
        return result.rowcount if result.rowcount is not None else 0

    @with_tenant_context
    def exists_promoted_hash(self, db: Session, tenant_id: uuid.UUID, dedupe_hash: str) -> bool:
        # RLS handles tenant_id filtering
        q = (
            db.query(ImportItem)
            .join(ImportBatch)
            .filter(
                ImportItem.dedupe_hash == dedupe_hash,
                ImportItem.status == "PROMOTED",
                # Prevent stale PROMOTED-without-id rows from blocking retries/idempotency.
                ImportItem.promoted_id.isnot(None),
            )
        )
        return db.query(q.exists()).scalar() or False
