"""Celery tasks for the importador module.

Async flow:
  1. POST /importador/run-async stores the uploaded payload and creates
     ImpDocumento(PENDING).
  2. importador.process_document processes the file and updates the document to
     REVIEW or FAILED.
  3. The frontend tracks batch progress until the state becomes terminal.
"""

from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
from pathlib import Path
from uuid import UUID

from .processing_service import RecipeContext, process_import_document

logger = logging.getLogger("importador.tasks")

LEGACY_REDIS_KEY_PREFIX = "imp:payload:"


def _payload_dir() -> Path:
    from app.config.settings import settings

    raw_dir = os.getenv("IMPORTADOR_PAYLOAD_DIR") or str(
        Path(settings.UPLOADS_DIR) / "_importador_payloads"
    )
    payload_dir = Path(raw_dir)
    payload_dir.mkdir(parents=True, exist_ok=True)
    return payload_dir


def _payload_path(doc_id: str | UUID) -> Path:
    return _payload_dir() / f"{doc_id}.bin"


def _get_redis():
    """Return a sync Redis client used for legacy payload fallback."""
    import redis  # type: ignore

    url = os.getenv("REDIS_URL") or os.getenv("DEV_REDIS_URL") or "redis://localhost:6379/0"
    return redis.from_url(url, decode_responses=False)


def store_payload(doc_id: str | UUID, file_bytes: bytes) -> None:
    """Store file bytes on local disk to avoid filling Redis memory."""
    payload_path = _payload_path(doc_id)
    tmp_path = payload_path.with_suffix(".tmp")
    tmp_path.write_bytes(file_bytes)
    tmp_path.replace(payload_path)


def load_payload(doc_id: str) -> bytes | None:
    """Load file bytes from disk; fallback to legacy Redis payloads."""
    payload_path = _payload_path(doc_id)
    if payload_path.exists():
        return payload_path.read_bytes()

    try:
        return _get_redis().get(f"{LEGACY_REDIS_KEY_PREFIX}{doc_id}")
    except Exception:
        return None


def delete_payload(doc_id: str) -> None:
    """Delete temporary payloads from disk and clear legacy Redis payloads."""
    try:
        _payload_path(doc_id).unlink(missing_ok=True)
    except Exception:
        logger.warning("No se pudo eliminar payload local de %s", doc_id, exc_info=True)

    try:
        _get_redis().delete(f"{LEGACY_REDIS_KEY_PREFIX}{doc_id}")
    except Exception:
        pass


def publish_batch_update(db, batch_id: UUID) -> None:
    from app.modules.importador import crud

    batch = crud.get_batch_any_tenant(db, batch_id)
    if batch is None:
        return

    payload = crud.serialize_batch_detail(db, batch)
    try:
        _get_redis().publish(f"imp:batch:{batch_id}", json.dumps(_json_safe(payload)))
    except Exception as exc:
        logger.warning("No se pudo publicar batch %s: %s", batch_id, exc)


from .utils import json_safe as _json_safe


async def _run_processing(
    doc_id: UUID,
    tenant_id: UUID,
    user_id: str | None,
    file_bytes: bytes,
    filename: str,
    tipo_archivo: str,
    recipe_snapshot_id: str | None = None,
    force: bool = False,
) -> None:
    """Run OCR + AI classification + field extraction and update ImpDocumento."""
    from app.config.database import SessionLocal
    from app.modules.importador import crud
    from app.modules.importador.ai_classifier import analyze_document
    from app.modules.importador.ocr_service import extract_text_from_file

    with SessionLocal() as db:
        from sqlalchemy import text as _text

        db.info["tenant_id"] = str(tenant_id)
        db.info["user_id"] = str(user_id) if user_id else None
        db.info["bypass_rls"] = True
        db.execute(_text("SELECT 1"))

        from app.models.importador import ImpDocumento

        doc = db.query(ImpDocumento).filter(ImpDocumento.id == doc_id).first()
        if doc is None:
            logger.error("Documento %s no encontrado en BD", doc_id)
            return

        crud.update_documento(db, doc, {"estado": "PROCESSING"})
        for batch_id in crud.touch_batch_items_for_document(db, doc.id, estado="PROCESSING"):
            crud.refresh_batch_status(db, batch_id)
            publish_batch_update(db, batch_id)
        db.commit()

        try:
            await process_import_document(
                mode="async",
                db=db,
                doc=doc,
                tenant_id=tenant_id,
                user_id=user_id,
                file_bytes=file_bytes,
                filename=filename,
                tipo_archivo=tipo_archivo,
                force=force,
                extract_text_fn=extract_text_from_file,
                analyze_document_fn=analyze_document,
                recipe_context=RecipeContext(
                    resolution_mode="snapshot" if recipe_snapshot_id else "zero_shot",
                    resolved_snapshot_id=recipe_snapshot_id,
                    explicit_recipe_context=bool(recipe_snapshot_id),
                ),
            )
            for batch_id in crud.touch_batch_items_for_document(db, doc.id, estado="REVIEW"):
                crud.refresh_batch_status(db, batch_id)
                publish_batch_update(db, batch_id)
            db.commit()
            logger.info("Documento %s procesado correctamente -> REVIEW", doc_id)

        except Exception as exc:
            logger.error("Error procesando documento %s: %s", doc_id, exc, exc_info=True)
            crud.update_documento(db, doc, {"estado": "FAILED", "error_detalle": str(exc)})
            crud.add_log(db, doc.id, "EXTRACT", user_id, {"error": str(exc)})
            for batch_id in crud.touch_batch_items_for_document(
                db,
                doc.id,
                estado="FAILED",
                error_detalle=str(exc),
            ):
                crud.refresh_batch_status(db, batch_id)
                publish_batch_update(db, batch_id)
            db.commit()


def _make_task():
    """Register the Celery task lazily to avoid startup failures."""
    try:
        from celery_app import celery_app  # type: ignore
    except Exception:
        return None

    @celery_app.task(
        name="importador.process_document",
        bind=True,
        queue="importador",
        max_retries=2,
        default_retry_delay=30,
        time_limit=420,
        soft_time_limit=390,
        acks_late=True,
        reject_on_worker_lost=True,
    )
    def process_document(
        self,
        doc_id: str,
        tenant_id: str,
        user_id: str | None,
        filename: str,
        tipo_archivo: str,
        recipe_snapshot_id: str | None = None,
        force: bool = False,
    ) -> dict:
        logger.info("Iniciando procesamiento async de documento %s (%s)", doc_id, filename)

        file_bytes = load_payload(doc_id)
        if not file_bytes:
            msg = f"Payload no encontrado para doc {doc_id}; puede haber expirado"
            logger.error(msg)
            try:
                from app.config.database import SessionLocal
                from app.models.importador import ImpDocumento
                from app.modules.importador import crud

                with SessionLocal() as db:
                    from sqlalchemy import text as _text

                    db.info["tenant_id"] = tenant_id
                    db.info["bypass_rls"] = True
                    db.execute(_text("SELECT 1"))
                    doc = db.query(ImpDocumento).filter(ImpDocumento.id == UUID(doc_id)).first()
                    if doc:
                        crud.update_documento(db, doc, {"estado": "FAILED", "error_detalle": msg})
                        for batch_id in crud.touch_batch_items_for_document(
                            db,
                            doc.id,
                            estado="FAILED",
                            error_detalle=msg,
                        ):
                            crud.refresh_batch_status(db, batch_id)
                            publish_batch_update(db, batch_id)
                        db.commit()
            except Exception as exc:
                logger.error("No se pudo marcar FAILED doc %s: %s", doc_id, exc)
            return {"ok": False, "error": msg}

        try:
            asyncio.run(
                _run_processing(
                    doc_id=UUID(doc_id),
                    tenant_id=UUID(tenant_id),
                    user_id=user_id,
                    file_bytes=file_bytes,
                    filename=filename,
                    tipo_archivo=tipo_archivo,
                    recipe_snapshot_id=recipe_snapshot_id,
                    force=force,
                )
            )
        except Exception as exc:
            logger.error("Task fallo para doc %s: %s", doc_id, exc, exc_info=True)
            try:
                raise self.retry(exc=exc)
            except self.MaxRetriesExceededError:
                return {"ok": False, "error": str(exc)}
        finally:
            delete_payload(doc_id)

        return {"ok": True, "doc_id": doc_id}

    return process_document


process_document_task = _make_task()
