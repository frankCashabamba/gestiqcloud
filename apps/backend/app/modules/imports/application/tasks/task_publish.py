"""Task: Publish - Promoción a tablas destino."""

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


class PublishTask(Task):
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True


def _impl(item_id: str, tenant_id: str, batch_id: str, task_id: str | None = None) -> dict:
    """
    Publica item a tablas destino (expenses/income/bank_movements).

    Args:
        item_id: UUID del ImportItem
        tenant_id: UUID del tenant
        batch_id: UUID del batch (correlation_id)

    Returns:
        dict con published status
    """
    item_uuid = UUID(item_id)
    tenant_uuid = UUID(tenant_id)

    logger.info(
        "Publishing item",
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

        if item.status != "validated":
            raise ValueError(f"Item {item_id} not validated")

        item.status = "publishing"
        item.updated_at = datetime.utcnow()
        db.commit()

        try:
            from app.modules.imports.domain.handlers import publish_to_destination

            destination_id = publish_to_destination(
                db=db,
                tenant_id=tenant_uuid,
                doc_type=item.doc_type or "desconocido",
                extracted_data=item.extracted_data or {},
            )

            metadata = item.metadata or {}
            metadata.update(
                {
                    "published_at": datetime.utcnow().isoformat(),
                    "destination_id": str(destination_id) if destination_id else None,
                    "publish_task_id": task_id,
                }
            )

            item.status = "published"
            item.metadata = metadata
            item.updated_at = datetime.utcnow()
            db.commit()

            logger.info(f"Item {item_id} published successfully")
            return {
                "status": "published",
                "item_id": item_id,
                "destination_id": str(destination_id) if destination_id else None,
            }

        except Exception as exc:
            item.status = "publish_failed"
            item.error = str(exc)
            item.updated_at = datetime.utcnow()
            db.commit()
            logger.error(f"Publish failed for {item_id}: {exc}")
            raise


if _celery_available and celery_app is not None:  # pragma: no cover

    @celery_app.task(base=PublishTask, bind=True, name="imports.publish")
    def publish_item(self, item_id: str, tenant_id: str, batch_id: str) -> dict:
        return _impl(item_id, tenant_id, batch_id, task_id=getattr(self.request, "id", None))

else:

    def publish_item(item_id: str, tenant_id: str, batch_id: str) -> dict:  # type: ignore
        return _impl(item_id, tenant_id, batch_id, task_id="inline")
