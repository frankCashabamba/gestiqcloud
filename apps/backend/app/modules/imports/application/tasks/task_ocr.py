"""Task: OCR - Extracción de texto via photo_utils."""

from __future__ import annotations

import logging
from uuid import UUID
from datetime import datetime

try:
    from celery import Task  # type: ignore

    _celery_available = True
except Exception:  # pragma: no cover

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


class OCRTask(Task):
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True


def _impl(
    item_id: str, tenant_id: str, batch_id: str, task_id: str | None = None
) -> dict:
    """
    Extrae texto del documento via OCR.

    Args:
        item_id: UUID del ImportItem
        tenant_id: UUID del tenant
        batch_id: UUID del batch (correlation_id)

    Returns:
        dict con texto extraído
    """
    item_uuid = UUID(item_id)
    tenant_uuid = UUID(tenant_id)

    logger.info(
        "OCR processing item",
        extra={
            "item_id": item_id,
            "tenant_id": tenant_id,
            "batch_id": batch_id,
            "task_id": task_id,
        },
    )

    with session_scope() as db:
        try:
            dialect = getattr(getattr(db, "bind", None), "dialect", None)
            if dialect and getattr(dialect, "name", "") == "postgresql":
                db.execute("SET LOCAL app.tenant_id = :tid", {"tid": str(tenant_uuid)})
        except Exception:
            pass

        item = db.query(ImportItem).filter(ImportItem.id == item_uuid).first()
        if not item:
            raise ValueError(f"Item {item_id} not found")

        item.status = "ocr_processing"
        item.updated_at = datetime.utcnow()
        db.commit()

        try:
            from app.modules.imports import services

            documentos = services.procesar_documento(
                bytes(item.file_data),
                item.filename or "documento.pdf",
            )

            serialized = []
            for doc in documentos:
                if hasattr(doc, "model_dump"):
                    serialized.append(doc.model_dump())
                elif isinstance(doc, dict):
                    serialized.append(doc)
                else:
                    serialized.append({"value": str(doc)})

            metadata = item.metadata or {}
            metadata.update(
                {
                    "ocr_processed_at": datetime.utcnow().isoformat(),
                    "ocr_documents_count": len(serialized),
                    "ocr_task_id": task_id,
                }
            )

            item.status = "ocr_completed"
            item.metadata = metadata
            item.ocr_result = {"documentos": serialized}
            item.updated_at = datetime.utcnow()
            db.commit()

            logger.info(f"OCR completed for {item_id}: {len(serialized)} documents")
            return {
                "status": "ocr_completed",
                "item_id": item_id,
                "documents_count": len(serialized),
            }

        except Exception as exc:
            item.status = "ocr_failed"
            item.error = str(exc)
            item.updated_at = datetime.utcnow()
            db.commit()
            logger.error(f"OCR failed for {item_id}: {exc}")
            raise


if _celery_available and celery_app is not None:  # pragma: no cover

    @celery_app.task(base=OCRTask, bind=True, name="imports.ocr")
    def ocr_item(self, item_id: str, tenant_id: str, batch_id: str) -> dict:
        return _impl(
            item_id, tenant_id, batch_id, task_id=getattr(self.request, "id", None)
        )
else:

    def ocr_item(item_id: str, tenant_id: str, batch_id: str) -> dict:  # type: ignore
        return _impl(item_id, tenant_id, batch_id, task_id="inline")
