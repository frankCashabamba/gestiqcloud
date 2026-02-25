"""Task: Validate - Validación por país (ES/EC)."""

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

try:
    from app.models.tenant import Tenant  # type: ignore
except Exception:  # pragma: no cover - optional in tests
    Tenant = None  # type: ignore

logger = logging.getLogger(__name__)


class ValidateTask(Task):
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True


def _impl(item_id: str, tenant_id: str, batch_id: str, task_id: str | None = None) -> dict:
    """
    Valida extracted_data según país del tenant.

    Args:
        item_id: UUID del ImportItem
        tenant_id: UUID del tenant
        batch_id: UUID del batch (correlation_id)

    Returns:
        dict con validation_result
    """
    item_uuid = UUID(item_id)
    tenant_uuid = UUID(tenant_id)

    logger.info(
        "Validating item",
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

        tenant = None
        try:
            if Tenant is not None:
                tenant = db.query(Tenant).filter(Tenant.id == tenant_uuid).first()
        except Exception:
            tenant = None

        item.status = "validating"
        item.updated_at = datetime.utcnow()
        db.commit()

        try:
            from app.modules.imports.validators.country_validators import (
                validate_ecuador,
                validate_spain,
            )

            country_code = "ES"
            try:
                if tenant and getattr(tenant, "country_code", None):
                    country_code = str(tenant.country_code).upper()
            except Exception:
                pass
            extracted_data = item.extracted_data or {}

            if country_code == "ES":
                validation_result = validate_spain(extracted_data, item.doc_type)
            elif country_code == "EC":
                validation_result = validate_ecuador(extracted_data, item.doc_type)
            else:
                validation_result = {
                    "valid": False,
                    "errors": [f"Unsupported country: {country_code}"],
                }

            metadata = item.metadata or {}
            metadata.update(
                {
                    "validated_at": datetime.utcnow().isoformat(),
                    "country_code": country_code,
                    "validate_task_id": task_id,
                }
            )

            if validation_result.get("valid"):
                item.status = "validated"
            else:
                item.status = "validation_failed"
                errors = validation_result.get("errors", [])
                item.error = "; ".join(errors[:3])

            item.validation_result = validation_result
            item.metadata = metadata
            item.updated_at = datetime.utcnow()
            db.commit()

            logger.info(f"Item {item_id} validated: {validation_result.get('valid')}")
            return {
                "status": item.status,
                "item_id": item_id,
                "valid": validation_result.get("valid"),
            }

        except Exception as exc:
            item.status = "validation_failed"
            item.error = str(exc)
            item.updated_at = datetime.utcnow()
            db.commit()
            logger.error(f"Validation failed for {item_id}: {exc}")
            raise


if _celery_available and celery_app is not None:  # pragma: no cover

    @celery_app.task(base=ValidateTask, bind=True, name="imports.validate")
    def validate_item(self, item_id: str, tenant_id: str, batch_id: str) -> dict:
        return _impl(item_id, tenant_id, batch_id, task_id=getattr(self.request, "id", None))

else:

    def validate_item(item_id: str, tenant_id: str, batch_id: str) -> dict:  # type: ignore
        return _impl(item_id, tenant_id, batch_id, task_id="inline")
