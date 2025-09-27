from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.config.database import session_scope
from app.models.core.modelsimport import ImportOCRJob
from app.modules.imports import services

_LOGGER = logging.getLogger("imports.ocr_jobs")


def _serialize_documentos(documentos: List[Any]) -> List[Dict[str, Any]]:
    serializable: List[Dict[str, Any]] = []
    for doc in documentos:
        if hasattr(doc, "model_dump"):
            serializable.append(doc.model_dump())  # type: ignore[attr-defined]
        elif isinstance(doc, dict):
            serializable.append(doc)
        else:
            try:
                serializable.append(dict(doc))
            except Exception:  # pragma: no cover - last resort
                serializable.append({"valor": str(doc)})
    return serializable


class OCRJobRunner:
    """Background worker que procesa trabajos OCR almacenados en BD."""

    def __init__(self, *, poll_interval: float = 1.0) -> None:
        self._poll_interval = poll_interval
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._reset_running_jobs()
        self._thread = threading.Thread(target=self._run, name="imports-ocr-runner", daemon=True)
        self._thread.start()
        _LOGGER.info("OCR job runner started")

    def stop(self, *, timeout: float = 5.0) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
            _LOGGER.info("OCR job runner stopped")

    def _reset_running_jobs(self) -> None:
        with session_scope() as db:
            now = datetime.utcnow()
            updated = (
                db.query(ImportOCRJob)
                .filter(ImportOCRJob.status == "running")
                .update(
                    {
                        ImportOCRJob.status: "pending",
                        ImportOCRJob.error: None,
                        ImportOCRJob.updated_at: now,
                    },
                    synchronize_session=False,
                )
            )
            if updated:
                _LOGGER.info("Reset %s stuck OCR jobs to pending", updated)

    def _claim_next_job(self, db: Session) -> Optional[ImportOCRJob]:
        query = (
            db.query(ImportOCRJob)
            .filter(ImportOCRJob.status == "pending")
            .order_by(ImportOCRJob.created_at.asc())
        )
        bind = getattr(db, "bind", None)
        if bind is not None and getattr(bind.dialect, "name", None) == "postgresql":  # pragma: no branch - dialect guard
            try:
                query = query.with_for_update(skip_locked=True)
            except Exception:
                pass
        job = query.first()
        if not job:
            return None
        job.status = "running"
        job.error = None
        job.updated_at = datetime.utcnow()
        db.add(job)
        db.flush()
        return job

    def _run(self) -> None:  # pragma: no cover - background thread
        while not self._stop_event.is_set():
            job_id: Optional[UUID] = None
            filename: Optional[str] = None
            payload: Optional[bytes] = None
            try:
                with session_scope() as db:
                    claimed = self._claim_next_job(db)
                    if claimed is None:
                        claimed = None
                    else:
                        job_id = claimed.id
                        filename = claimed.filename
                        payload = bytes(claimed.payload or b"")
                if job_id is None or payload is None or filename is None:
                    self._stop_event.wait(self._poll_interval)
                    continue
                self._process_job(job_id, filename, payload)
            except Exception:
                _LOGGER.exception("Unexpected error in OCR job runner loop")
                self._stop_event.wait(self._poll_interval)
            finally:
                payload = None

    def _process_job(self, job_id: UUID, filename: str, payload: bytes) -> None:
        try:
            documentos = services.procesar_documento(payload, filename)
            result = {"archivo": filename, "documentos": _serialize_documentos(documentos)}
            self._update_job(job_id, status="done", result=result, error=None)
        except Exception as exc:  # pragma: no cover - best effort logging
            _LOGGER.exception("Failed to process OCR job %s", job_id)
            self._update_job(job_id, status="failed", result=None, error=str(exc))

    def _update_job(
        self,
        job_id: UUID,
        *,
        status: str,
        result: Optional[Dict[str, Any]],
        error: Optional[str],
    ) -> None:
        with session_scope() as db:
            job = db.query(ImportOCRJob).filter(ImportOCRJob.id == job_id).first()
            if not job:
                return
            job.status = status
            job.result = result
            job.error = error
            job.updated_at = datetime.utcnow()
            db.add(job)


def enqueue_job(*, empresa_id: int, filename: str, content_type: Optional[str], payload: bytes) -> UUID:
    """Inserta un trabajo OCR y devuelve su id."""
    with session_scope() as db:
        job = ImportOCRJob(
            id=uuid4(),
            empresa_id=empresa_id,
            filename=filename,
            content_type=content_type,
            payload=payload,
        )
        db.add(job)
        db.flush()
        return job.id


job_runner = OCRJobRunner()
