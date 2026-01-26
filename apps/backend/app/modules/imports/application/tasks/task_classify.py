"""Task: Classify - Clasificación de doc_type (factura/recibo/banco)."""

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


class ClassifyTask(Task):
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True


def _classify_document(ocr_result: dict) -> str:
    """
    Clasifica tipo de documento basado en palabras clave del OCR.

    Returns:
        'factura', 'recibo', 'banco', 'transferencia', 'ticket_pos', 'desconocido'
    """
    documentos = ocr_result.get("documentos", [])
    if not documentos:
        return "desconocido"

    text = ""
    for doc in documentos:
        if isinstance(doc, dict):
            for key in ["texto", "text", "content"]:
                if key in doc:
                    text += str(doc[key]).lower() + " "
        else:
            text += str(doc).lower() + " "

    keywords = {
        "ticket_pos": [
            "ticket de venta",
            "ticket venta",
            "nº r-",
            "n° r-",
            "gracias por su compra",
            "gracias por tu compra",
            "productos",
            "estado: paid",
        ],
        "factura": ["factura", "invoice", "nif", "cif", "iva", "ruc", "nit"],
        "recibo": ["recibo", "receipt", "comprobante", "paid"],
        "banco": ["extracto", "saldo", "iban", "banco", "bank statement", "movimientos"],
        "transferencia": [
            "transferencia",
            "transfer",
            "wire",
            "swift",
            "ordenante",
            "beneficiario",
        ],
    }

    scores = {}
    for doc_type, words in keywords.items():
        scores[doc_type] = sum(1 for w in words if w in text)

    # Bonus para ticket_pos si tiene formato de línea de producto (10x producto - $1.50)
    import re

    if re.search(r"\d+[.,]?\d*\s*x\s+.+", text):
        scores["ticket_pos"] = scores.get("ticket_pos", 0) + 2

    max_score = max(scores.values())
    if max_score == 0:
        return "desconocido"

    return max(scores, key=scores.get)


def _impl(item_id: str, tenant_id: str, batch_id: str, task_id: str | None = None) -> dict:
    """
    Clasifica tipo de documento.

    Args:
        item_id: UUID del ImportItem
        tenant_id: UUID del tenant
        batch_id: UUID del batch (correlation_id)

    Returns:
        dict con doc_type clasificado
    """
    item_uuid = UUID(item_id)
    tenant_uuid = UUID(tenant_id)

    logger.info(
        "Classifying item",
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

        item.status = "classifying"
        item.updated_at = datetime.utcnow()
        db.commit()

        try:
            ocr_result = item.ocr_result or {}
            doc_type = _classify_document(ocr_result)

            metadata = item.metadata or {}
            metadata.update(
                {
                    "classified_at": datetime.utcnow().isoformat(),
                    "classify_task_id": task_id,
                }
            )

            item.status = "classified"
            item.doc_type = doc_type
            item.metadata = metadata
            item.updated_at = datetime.utcnow()
            db.commit()

            logger.info(f"Item {item_id} classified as {doc_type}")
            return {
                "status": "classified",
                "item_id": item_id,
                "doc_type": doc_type,
            }

        except Exception as exc:
            item.status = "classification_failed"
            item.error = str(exc)
            item.updated_at = datetime.utcnow()
            db.commit()
            logger.error(f"Classification failed for {item_id}: {exc}")
            raise


if _celery_available and celery_app is not None:  # pragma: no cover

    @celery_app.task(base=ClassifyTask, bind=True, name="imports.classify")
    def classify_item(self, item_id: str, tenant_id: str, batch_id: str) -> dict:
        return _impl(item_id, tenant_id, batch_id, task_id=getattr(self.request, "id", None))

else:

    def classify_item(item_id: str, tenant_id: str, batch_id: str) -> dict:  # type: ignore
        return _impl(item_id, tenant_id, batch_id, task_id="inline")
