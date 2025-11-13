"""Pipeline orchestration para imports con Celery chains y DLQ."""

from __future__ import annotations

import logging
import os
from uuid import UUID
from typing import Optional

try:
    from celery import chain, group

    _celery_available = True
except Exception:  # pragma: no cover - optional in tests
    chain = group = None  # type: ignore
    _celery_available = False
from sqlalchemy.orm import Session

try:
    from app.modules.imports.application.celery_app import celery_app, RUNNER_MODE
except Exception:  # pragma: no cover - allow running without Celery
    celery_app = None  # type: ignore
    RUNNER_MODE = os.getenv("IMPORTS_RUNNER_MODE", "inline")
from app.modules.imports.application.tasks.task_preprocess import preprocess_item
from app.modules.imports.application.tasks.task_ocr import ocr_item
from app.modules.imports.application.tasks.task_classify import classify_item
from app.modules.imports.application.tasks.task_extract import extract_item
from app.modules.imports.application.tasks.task_validate import validate_item
from app.modules.imports.application.tasks.task_publish import publish_item
from app.config.database import session_scope
from app.models.core.modelsimport import ImportItem, ImportBatch

logger = logging.getLogger(__name__)


def enqueue_item_pipeline(
    item_id: UUID,
    tenant_id: UUID,
    batch_id: UUID,
    db: Optional[Session] = None,
) -> str:
    """
    Enqueue pipeline completo para un item.

    Pipeline: preprocess → ocr → classify → extract → validate → publish

    Args:
        item_id: UUID del ImportItem
        tenant_id: UUID del tenant
        batch_id: UUID del batch (correlation_id)
        db: Session opcional (si ya tienes una abierta)

    Returns:
        task_id del chain
    """
    item_str = str(item_id)
    tenant_str = str(tenant_id)
    batch_str = str(batch_id)

    if RUNNER_MODE == "inline" or not _celery_available:
        logger.info(f"Running item {item_str} inline (no Celery)")
        _run_inline(item_str, tenant_str, batch_str)
        return "inline"

    workflow = chain(
        preprocess_item.s(item_str, tenant_str, batch_str),
        ocr_item.s(tenant_str, batch_str),
        classify_item.s(tenant_str, batch_str),
        extract_item.s(tenant_str, batch_str),
        validate_item.s(tenant_str, batch_str),
        publish_item.s(tenant_str, batch_str),
    )

    result = workflow.apply_async()
    logger.info(
        f"Enqueued pipeline for item {item_str}, chain_id={result.id}",
        extra={"item_id": item_str, "tenant_id": tenant_str, "batch_id": batch_str},
    )
    return result.id


def enqueue_batch_pipeline(batch_id: UUID, tenant_id: UUID) -> dict:
    """
    Enqueue pipeline para todos los items de un batch.

    Args:
        batch_id: UUID del ImportBatch
        tenant_id: UUID del tenant

    Returns:
        dict con counts y group_id
    """
    batch_str = str(batch_id)
    tenant_str = str(tenant_id)

    with session_scope() as db:
        # Skip SET LOCAL in non-Postgres test environments
        try:
            dialect = getattr(getattr(db, "bind", None), "dialect", None)
            if dialect and getattr(dialect, "name", "") == "postgresql":
                db.execute("SET LOCAL app.tenant_id = :tid", {"tid": tenant_str})
        except Exception:
            pass

        batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
        if not batch:
            raise ValueError(f"Batch {batch_str} not found")

        items = (
            db.query(ImportItem)
            .filter(ImportItem.batch_id == batch_id)
            .filter(ImportItem.status.in_(["pending", "failed"]))
            .all()
        )

        if not items:
            logger.info(f"No items to process in batch {batch_str}")
            return {"enqueued": 0, "batch_id": batch_str}

        if RUNNER_MODE == "inline" or not _celery_available:
            for item in items:
                _run_inline(str(item.id), tenant_str, batch_str)
            return {"enqueued": len(items), "batch_id": batch_str, "mode": "inline"}

        job = group(
            chain(
                preprocess_item.s(str(item.id), tenant_str, batch_str),
                ocr_item.s(tenant_str, batch_str),
                classify_item.s(tenant_str, batch_str),
                extract_item.s(tenant_str, batch_str),
                validate_item.s(tenant_str, batch_str),
            )
            for item in items
        )

        if not _celery_available or celery_app is None:
            logger.info("Celery not available, falling back to inline group execution")
            for item in items:
                _run_inline(str(item.id), tenant_str, batch_str)
            return {"enqueued": len(items), "batch_id": batch_str, "mode": "inline"}
        result = job.apply_async()
        logger.info(
            f"Enqueued batch {batch_str}: {len(items)} items, group_id={result.id}",
            extra={"batch_id": batch_str, "tenant_id": tenant_str, "count": len(items)},
        )

        return {
            "enqueued": len(items),
            "batch_id": batch_str,
            "group_id": result.id,
        }


def _run_inline(item_id: str, tenant_id: str, batch_id: str) -> None:
    """Ejecuta pipeline inline (sin Celery) para dev/tests."""
    try:
        preprocess_item(item_id, tenant_id, batch_id)
        result = ocr_item(item_id, tenant_id, batch_id)
        item_id_next = result["item_id"]

        result = classify_item(item_id_next, tenant_id, batch_id)
        item_id_next = result["item_id"]

        result = extract_item(item_id_next, tenant_id, batch_id)
        item_id_next = result["item_id"]

        result = validate_item(item_id_next, tenant_id, batch_id)

        if result.get("valid"):
            publish_item(item_id_next, tenant_id, batch_id)
    except Exception as exc:
        logger.exception(f"Inline pipeline failed for {item_id}: {exc}")
        with session_scope() as db:
            try:
                dialect = getattr(getattr(db, "bind", None), "dialect", None)
                if dialect and getattr(dialect, "name", "") == "postgresql":
                    db.execute("SET LOCAL app.tenant_id = :tid", {"tid": tenant_id})
            except Exception:
                pass
            item = db.query(ImportItem).filter(ImportItem.id == UUID(item_id)).first()
            if item:
                item.status = "failed"
                item.error = str(exc)
                db.commit()


def retry_failed_items(batch_id: UUID, tenant_id: UUID) -> dict:
    """
    Re-encola items fallidos de un batch.

    Args:
        batch_id: UUID del ImportBatch
        tenant_id: UUID del tenant

    Returns:
        dict con counts
    """
    batch_str = str(batch_id)
    tenant_str = str(tenant_id)

    with session_scope() as db:
        try:
            dialect = getattr(getattr(db, "bind", None), "dialect", None)
            if dialect and getattr(dialect, "name", "") == "postgresql":
                db.execute("SET LOCAL app.tenant_id = :tid", {"tid": tenant_str})
        except Exception:
            pass

        items = (
            db.query(ImportItem)
            .filter(ImportItem.batch_id == batch_id)
            .filter(ImportItem.status.like("%failed"))
            .all()
        )

        if not items:
            logger.info(f"No failed items to retry in batch {batch_str}")
            return {"retried": 0, "batch_id": batch_str}

        for item in items:
            item.status = "pending"
            item.error = None
        db.commit()

        for item in items:
            enqueue_item_pipeline(item.id, tenant_id, batch_id, db=db)

        logger.info(f"Retried {len(items)} failed items in batch {batch_str}")
        return {"retried": len(items), "batch_id": batch_str}
