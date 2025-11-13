"""Task: Extract - Extracción de campos y normalización canónica."""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

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


class ExtractTask(Task):
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True


def _impl(item_id: str, tenant_id: str, batch_id: str, task_id: str | None = None) -> dict:
    """
    Extrae campos y normaliza a schema canónico.

    Args:
        item_id: UUID del ImportItem
        tenant_id: UUID del tenant
        batch_id: UUID del batch (correlation_id)

    Returns:
        dict con extracted_data canónico
    """
    item_uuid = UUID(item_id)
    tenant_uuid = UUID(tenant_id)

    logger.info(
        "Extracting item",
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

        item.status = "extracting"
        item.updated_at = datetime.utcnow()
        db.commit()

        try:
            from app.modules.imports.extractores import (
                extractor_banco,
                extractor_desconocido,
                extractor_factura,
                extractor_recibo,
                extractor_transferencia,
            )

            doc_type = item.doc_type or "desconocido"
            ocr_result = item.ocr_result or {}
            documentos = ocr_result.get("documentos", [])

            if not documentos:
                raise ValueError("No OCR documents to extract from")

            extractor_map = {
                "factura": extractor_factura.extraer,
                "recibo": extractor_recibo.extraer,
                "banco": extractor_banco.extraer,
                "transferencia": extractor_transferencia.extraer,
                "desconocido": extractor_desconocido.extraer,
            }

            extractor = extractor_map.get(doc_type, extractor_desconocido.extraer)
            extracted_data = extractor(documentos[0])

            metadata = item.metadata or {}
            metadata.update(
                {
                    "extracted_at": datetime.utcnow().isoformat(),
                    "extract_task_id": task_id,
                }
            )

            item.status = "extracted"
            item.extracted_data = extracted_data
            item.metadata = metadata
            item.updated_at = datetime.utcnow()
            db.commit()

            logger.info(f"Item {item_id} extracted successfully")
            return {
                "status": "extracted",
                "item_id": item_id,
                "doc_type": doc_type,
            }

        except Exception as exc:
            item.status = "extraction_failed"
            item.error = str(exc)
            item.updated_at = datetime.utcnow()
            db.commit()
            logger.error(f"Extraction failed for {item_id}: {exc}")
            raise


if _celery_available and celery_app is not None:  # pragma: no cover

    @celery_app.task(base=ExtractTask, bind=True, name="imports.extract")
    def extract_item(self, item_id: str, tenant_id: str, batch_id: str) -> dict:
        return _impl(item_id, tenant_id, batch_id, task_id=getattr(self.request, "id", None))

else:

    def extract_item(item_id: str, tenant_id: str, batch_id: str) -> dict:  # type: ignore
        return _impl(item_id, tenant_id, batch_id, task_id="inline")
