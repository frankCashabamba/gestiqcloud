"""Task: Promote - Promoción de documento canónico a tablas destino.

Fase C: Promueve documentos validados (canonical_doc) a sus tablas destino
usando handlers especializados según doc_type.

Flujo:
  1. ImportItem.canonical_doc validado (status='OK')
  2. HandlersRouter.promote_canonical() despecha al handler correcto
  3. Handler inserta en tabla destino (invoices, gastos, bank_transactions, products, etc)
  4. ImportItem se marca como PROMOTED con promoted_id y promoted_to
"""

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
from app.db.rls import set_tenant_guc
from app.models.core.modelsimport import ImportBatch, ImportItem
from app.modules.imports.domain.canonical_schema import validate_canonical
from app.modules.imports.domain.handlers_router import HandlersRouter

logger = logging.getLogger(__name__)


class PromoteTask(Task):
    """Celery task config para promover items."""

    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 2}
    retry_backoff = True
    retry_backoff_max = 300
    retry_jitter = True


def _impl_promote_item(
    item_id: str,
    tenant_id: str,
    batch_id: str,
    task_id: str | None = None,
) -> dict:
    """
    Promueve un ImportItem validado a su tabla destino.

    Args:
        item_id: UUID del ImportItem
        tenant_id: UUID del tenant
        batch_id: UUID del batch
        task_id: Celery task ID (para trazabilidad)

    Returns:
        {
            "ok": True/False,
            "item_id": str,
            "promoted": True/False,
            "promoted_to": "invoices" | "gastos" | "bank_transactions" | "products",
            "promoted_id": str (UUID of created record),
            "error": str (si falló)
        }
    """
    item_uuid = UUID(item_id)
    tenant_uuid = UUID(tenant_id)
    UUID(batch_id)

    logger.info(
        "Promoting item to destination",
        extra={
            "item_id": item_id,
            "tenant_id": tenant_id,
            "batch_id": batch_id,
            "task_id": task_id,
        },
    )

    with session_scope() as db:
        # Set tenant GUC for RLS
        try:
            set_tenant_guc(db, str(tenant_uuid), persist=False)
        except Exception:
            pass

        try:
            # Get ImportItem
            item = db.query(ImportItem).filter(ImportItem.id == item_uuid).first()
            if not item:
                return {
                    "ok": False,
                    "item_id": item_id,
                    "promoted": False,
                    "error": f"Item {item_id} not found",
                }

            # Verificar status
            if item.status not in ("OK", "ERROR_VALIDATION"):
                # Si ya está promovido, retornar
                if item.promoted_id:
                    return {
                        "ok": True,
                        "item_id": item_id,
                        "promoted": True,
                        "promoted_to": item.promoted_to,
                        "promoted_id": str(item.promoted_id),
                        "skipped": True,
                    }
                return {
                    "ok": False,
                    "item_id": item_id,
                    "promoted": False,
                    "error": f"Item status={item.status} not promotable. Expected OK or ERROR_VALIDATION",
                }

            # Obtener documento canónico
            canonical_doc = item.canonical_doc
            if not canonical_doc:
                return {
                    "ok": False,
                    "item_id": item_id,
                    "promoted": False,
                    "error": "No canonical_doc available for promotion",
                }

            # Revalidar documento canónico (seguridad)
            is_valid, errors = validate_canonical(canonical_doc)
            if not is_valid:
                item.status = "ERROR_VALIDATION"
                item.errors = errors
                try:
                    db.commit()
                except Exception as commit_error:
                    db.rollback()
                    logger.error(f"Failed to commit validation error for {item_id}: {commit_error}")
                logger.warning(
                    f"Canonical doc failed revalidation: {errors}",
                    extra={"item_id": item_id},
                )
                return {
                    "ok": False,
                    "item_id": item_id,
                    "promoted": False,
                    "error": f"Canonical doc validation failed: {errors}",
                }

            # Promover usando HandlersRouter
            doc_type = canonical_doc.get("doc_type", "other")
            try:
                promote_result = HandlersRouter.promote_canonical(
                    db=db,
                    tenant_id=tenant_uuid,
                    canonical_doc=canonical_doc,
                )

                if not promote_result:
                    return {
                        "ok": False,
                        "item_id": item_id,
                        "promoted": False,
                        "error": f"Handler returned no result for doc_type={doc_type}",
                    }

                # Actualizar ImportItem con resultado
                promoted_id = promote_result.get("domain_id")
                promoted_to = promote_result.get("target")

                item.status = "PROMOTED"
                item.promoted_to = promoted_to
                item.promoted_id = UUID(promoted_id) if promoted_id else None
                item.promoted_at = datetime.utcnow()
                try:
                    db.commit()
                except Exception as commit_error:
                    db.rollback()
                    logger.error(f"Failed to commit promotion for {item_id}: {commit_error}")
                    raise

                logger.info(
                    f"Item {item_id} promoted successfully",
                    extra={
                        "promoted_to": promoted_to,
                        "promoted_id": promoted_id,
                    },
                )

                return {
                    "ok": True,
                    "item_id": item_id,
                    "promoted": True,
                    "promoted_to": promoted_to,
                    "promoted_id": promoted_id,
                }

            except Exception as handler_error:
                item.status = "ERROR_PROMOTION"
                item.errors = item.errors or []
                item.errors.append(
                    {
                        "phase": "promotion",
                        "doc_type": doc_type,
                        "message": str(handler_error),
                    }
                )
                try:
                    db.commit()
                except Exception as commit_error:
                    db.rollback()
                    logger.error(f"Failed to commit error status for {item_id}: {commit_error}")
                logger.error(
                    f"Promotion failed for {item_id}: {handler_error}",
                    extra={"item_id": item_id},
                )
                raise

        except Exception as e:
            try:
                db.rollback()
            except Exception:
                pass
            logger.error(
                f"Promote task failed: {e}",
                extra={
                    "item_id": item_id,
                    "batch_id": batch_id,
                    "tenant_id": tenant_id,
                },
            )
            raise


def _impl_promote_batch(
    batch_id: str,
    tenant_id: str,
    task_id: str | None = None,
) -> dict:
    """
    Promueve todos los items OK de un batch.

    Args:
        batch_id: UUID del batch
        tenant_id: UUID del tenant
        task_id: Celery task ID

    Returns:
        {
            "ok": True/False,
            "batch_id": str,
            "promoted": int,
            "failed": int,
            "skipped": int,
        }
    """
    batch_uuid = UUID(batch_id)
    tenant_uuid = UUID(tenant_id)

    logger.info(
        "Promoting batch",
        extra={
            "batch_id": batch_id,
            "tenant_id": tenant_id,
            "task_id": task_id,
        },
    )

    with session_scope() as db:
        try:
            set_tenant_guc(db, str(tenant_uuid), persist=False)
        except Exception:
            pass

        try:
            # Obtener batch
            batch = db.query(ImportBatch).filter(ImportBatch.id == batch_uuid).first()
            if not batch:
                return {
                    "ok": False,
                    "batch_id": batch_id,
                    "promoted": 0,
                    "failed": 0,
                    "skipped": 0,
                    "error": f"Batch {batch_id} not found",
                }

            batch.status = "PROMOTING"
            try:
                db.commit()
            except Exception as commit_error:
                db.rollback()
                logger.error(f"Failed to commit batch status update: {commit_error}")
                raise

            # Obtener items para promover
            items = (
                db.query(ImportItem)
                .filter(
                    ImportItem.batch_id == batch_uuid,
                    ImportItem.status.in_(("OK", "ERROR_VALIDATION")),
                    ImportItem.canonical_doc.isnot(None),
                )
                .all()
            )

            promoted = 0
            failed = 0
            skipped = 0

            for item in items:
                try:
                    # Usar HandlersRouter para cada item
                    canonical_doc = item.canonical_doc
                    is_valid, errors = validate_canonical(canonical_doc)

                    if not is_valid:
                        item.status = "ERROR_VALIDATION"
                        item.errors = errors
                        failed += 1
                        continue

                    promote_result = HandlersRouter.promote_canonical(
                        db=db,
                        tenant_id=tenant_uuid,
                        canonical_doc=canonical_doc,
                    )

                    if promote_result:
                        item.status = "PROMOTED"
                        item.promoted_to = promote_result.get("target")
                        item.promoted_id = (
                            UUID(promote_result.get("domain_id"))
                            if promote_result.get("domain_id")
                            else None
                        )
                        item.promoted_at = datetime.utcnow()
                        promoted += 1
                    else:
                        failed += 1

                except Exception as e:
                    item.status = "ERROR_PROMOTION"
                    item.errors = [{"phase": "promotion", "message": str(e)}]
                    failed += 1
                    logger.warning(f"Failed to promote item {item.id}: {e}")

            try:
                db.commit()
            except Exception as commit_error:
                db.rollback()
                logger.error(f"Failed to commit items promotion: {commit_error}")
                raise

            batch.status = "PROMOTED"
            try:
                db.commit()
            except Exception as commit_error:
                db.rollback()
                logger.error(f"Failed to commit batch status to PROMOTED: {commit_error}")
                raise

            return {
                "ok": True,
                "batch_id": batch_id,
                "promoted": promoted,
                "failed": failed,
                "skipped": skipped,
            }

        except Exception as e:
            if batch:
                batch.status = "ERROR"
                try:
                    db.commit()
                except Exception as commit_error:
                    db.rollback()
                    logger.error(f"Failed to commit batch error status: {commit_error}")
            logger.error(f"Batch promotion failed: {e}")
            raise


# Celery task definitions
if _celery_available and celery_app is not None:  # pragma: no cover

    @celery_app.task(base=PromoteTask, bind=True, name="imports.promote_item")
    def promote_item(self, item_id: str, tenant_id: str, batch_id: str) -> dict:
        """Promueve un item individual."""
        return _impl_promote_item(
            item_id, tenant_id, batch_id, task_id=getattr(self.request, "id", None)
        )

    @celery_app.task(base=PromoteTask, bind=True, name="imports.promote_batch")
    def promote_batch(self, batch_id: str, tenant_id: str) -> dict:
        """Promueve todos los items de un batch."""
        return _impl_promote_batch(batch_id, tenant_id, task_id=getattr(self.request, "id", None))

else:

    def promote_item(item_id: str, tenant_id: str, batch_id: str) -> dict:  # type: ignore
        """Fallback para modo no-Celery."""
        return _impl_promote_item(item_id, tenant_id, batch_id, task_id="inline")

    def promote_batch(batch_id: str, tenant_id: str) -> dict:  # type: ignore
        """Fallback para modo no-Celery."""
        return _impl_promote_batch(batch_id, tenant_id, task_id="inline")
