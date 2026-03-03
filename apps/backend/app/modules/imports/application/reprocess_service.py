from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.core.modelsimport import ImportBatch, ImportItem, ImportMapping
from app.modules.imports.application.transform_dsl import apply_mapping_pipeline

logger = logging.getLogger(__name__)


class ReprocessService:

    def __init__(self, db: Session) -> None:
        self.db = db

    def reprocess_batch(
        self,
        batch_id: UUID,
        tenant_id: str,
        template_id: UUID | None = None,
    ) -> dict[str, int]:
        batch: ImportBatch | None = (
            self.db.query(ImportBatch)
            .filter(ImportBatch.id == batch_id, ImportBatch.tenant_id == tenant_id)
            .first()
        )
        if batch is None:
            raise ValueError(f"Batch {batch_id} not found for tenant {tenant_id}")

        mapping = self._load_template(batch, template_id)

        items: list[ImportItem] = (
            self.db.query(ImportItem)
            .filter(ImportItem.batch_id == batch_id)
            .order_by(ImportItem.idx)
            .all()
        )

        reprocessed = 0
        errors = 0

        map_cfg = mapping.mappings if mapping else None
        tf_cfg = mapping.transforms if mapping else None
        df_cfg = mapping.defaults if mapping else None

        for item in items:
            try:
                raw: dict[str, Any] = item.raw or {}
                tables = raw.get("tables", [])
                if tables:
                    table = tables[0]
                    headers = table.get("headers_raw", [])
                    row_data = table.get("rows", [{}])[0] if table.get("rows") else {}
                    values = [row_data.get(h) for h in headers]
                else:
                    headers = list(raw.get("kv", {}).keys())
                    values = list(raw.get("kv", {}).values())

                if map_cfg or tf_cfg or df_cfg:
                    normalized = apply_mapping_pipeline(
                        headers,
                        values,
                        mapping=map_cfg or {},
                        transforms=tf_cfg or {},
                        defaults=df_cfg or {},
                    )
                else:
                    normalized = dict(zip(headers, values))

                item.normalized = normalized
                item.errors = []
                item.status = "PENDING"
                reprocessed += 1
            except Exception:
                logger.exception("Error reprocessing item %s", item.id)
                item.status = "ERROR_VALIDATION"
                errors += 1

        if mapping and batch.mapping_id != mapping.id:
            batch.mapping_id = mapping.id

        self.db.flush()

        return {"reprocessed": reprocessed, "errors": errors}

    def _load_template(
        self,
        batch: ImportBatch,
        template_id: UUID | None,
    ) -> ImportMapping | None:
        if template_id:
            mapping = (
                self.db.query(ImportMapping)
                .filter(
                    ImportMapping.id == template_id,
                    ImportMapping.tenant_id == batch.tenant_id,
                )
                .first()
            )
            if mapping is None:
                raise ValueError(f"Template {template_id} not found")
            return mapping

        if batch.mapping_id:
            return self.db.query(ImportMapping).filter(ImportMapping.id == batch.mapping_id).first()

        return (
            self.db.query(ImportMapping)
            .filter(
                ImportMapping.tenant_id == batch.tenant_id,
                ImportMapping.source_type == batch.source_type,
            )
            .order_by(ImportMapping.version.desc())
            .first()
        )
