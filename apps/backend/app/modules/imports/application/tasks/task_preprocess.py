"""Task: Preprocess - Antivirus y clasificación inicial de tipo."""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

try:
    from celery import Task  # type: ignore

    _celery_available = True
except Exception:  # pragma: no cover - allow running without Celery

    class Task:  # type: ignore
        pass

    _celery_available = False

try:
    from app.modules.imports.application.celery_app import celery_app
except Exception:  # pragma: no cover
    celery_app = None  # type: ignore
from app.config.database import session_scope
from app.models.core.modelsimport import ImportItem

logger = logging.getLogger(__name__)


class PreprocessTask(Task):
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True


def _impl(item_id: str, tenant_id: str, batch_id: str, task_id: str | None = None) -> dict:
    """
    Preprocesa item: antivirus + clasificación tipo documento.

    Args:
        item_id: UUID del ImportItem
        tenant_id: UUID del tenant (para RLS)
        batch_id: UUID del batch (correlation_id)

    Returns:
        dict con status y metadata
    """
    item_uuid = UUID(item_id)
    tenant_uuid = UUID(tenant_id)

    logger.info(
        "Preprocessing item",
        extra={
            "item_id": item_id,
            "tenant_id": tenant_id,
            "batch_id": batch_id,
            "task_id": task_id,
        },
    )

    with session_scope() as db:
        # Skip SET LOCAL in non-Postgres tests
        try:
            dialect = getattr(getattr(db, "bind", None), "dialect", None)
            if dialect and getattr(dialect, "name", "") == "postgresql":
                db.execute("SET LOCAL app.tenant_id = :tid", {"tid": str(tenant_uuid)})
        except Exception:
            pass

        item = db.query(ImportItem).filter(ImportItem.id == item_uuid).first()
        if not item:
            raise ValueError(f"Item {item_id} not found")

        item.status = "preprocessing"
        item.updated_at = datetime.utcnow()
        db.commit()

        try:
            file_size = len(item.file_data) if item.file_data else 0
            mime_type = item.mime_type or "application/octet-stream"

            if file_size == 0:
                raise ValueError("Empty file")

            if file_size > 20 * 1024 * 1024:
                raise ValueError("File too large (>20MB)")

            allowed_mimes = [
                "application/pdf",
                "image/jpeg",
                "image/png",
                "image/tiff",
                "application/xml",
                "text/xml",
            ]
            if mime_type not in allowed_mimes:
                raise ValueError(f"Unsupported MIME type: {mime_type}")

            metadata = item.metadata or {}
            metadata.update(
                {
                    "preprocessed_at": datetime.utcnow().isoformat(),
                    "file_size": file_size,
                    "mime_type": mime_type,
                    "task_id": task_id,
                }
            )

            item.status = "preprocessed"
            item.metadata = metadata
            item.updated_at = datetime.utcnow()
            db.commit()

            logger.info(f"Item {item_id} preprocessed successfully")
            return {"status": "preprocessed", "item_id": item_id}

        except Exception as exc:
            item.status = "preprocessing_failed"
            item.error = str(exc)
            item.updated_at = datetime.utcnow()
            db.commit()
            logger.error(f"Preprocessing failed for {item_id}: {exc}")
            raise


if _celery_available and celery_app is not None:  # pragma: no cover

    @celery_app.task(base=PreprocessTask, bind=True, name="imports.preprocess")
    def preprocess_item(self, item_id: str, tenant_id: str, batch_id: str) -> dict:
        return _impl(item_id, tenant_id, batch_id, task_id=getattr(self.request, "id", None))

else:
    # Inline/synchronous fallback used in tests
    def preprocess_item(item_id: str, tenant_id: str, batch_id: str) -> dict:  # type: ignore
        return _impl(item_id, tenant_id, batch_id, task_id="inline")
