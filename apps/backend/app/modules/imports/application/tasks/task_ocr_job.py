"""Celery task para procesar ImportOCRJob usando el pipeline OCR."""

from __future__ import annotations

from uuid import UUID

from app.modules.imports.application.celery_app import celery_app
from app.modules.imports.application.job_runner import process_ocr_job


@celery_app.task(name="imports.process_ocr_job", bind=True)
def process_ocr_job_task(self, job_id: str) -> dict:
    return process_ocr_job(UUID(job_id))
