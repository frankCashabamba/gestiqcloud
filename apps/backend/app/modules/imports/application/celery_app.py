"""Celery app para procesamiento asíncrono de imports."""

from __future__ import annotations

import os
import warnings

from celery import Celery
from kombu import Queue


def _get_redis_url_for_imports() -> str:
    """
    Get Redis URL for imports Celery broker with validation.

    In production: Fails explicitly if REDIS_URL is not configured
    In development: Warns if using localhost fallback
    """
    redis_url = os.getenv("REDIS_URL", "").strip()
    if redis_url:
        return redis_url

    environment = os.getenv("ENVIRONMENT", "development").lower()
    if environment == "production":
        raise RuntimeError(
            "REDIS_URL is not configured. Required for imports Celery broker. "
            "Example: REDIS_URL=redis://cache.internal:6379/1"
        )

    warnings.warn(
        "REDIS_URL not configured. Using development fallback (localhost).", RuntimeWarning
    )
    return "redis://localhost:6379/0"


def _get_redis_result_url() -> str:
    """Get Redis URL for Celery result backend with validation."""
    # Try REDIS_RESULT_URL first, then fall back to REDIS_URL pattern
    redis_url = os.getenv("REDIS_RESULT_URL", "").strip()
    if redis_url:
        return redis_url

    # Try REDIS_URL and adjust database
    redis_base = os.getenv("REDIS_URL", "").strip()
    if redis_base:
        # Append /1 if base is /0, otherwise assume it's configured correctly
        if redis_base.endswith("/0"):
            return redis_base[:-1] + "1"
        return redis_base

    environment = os.getenv("ENVIRONMENT", "development").lower()
    if environment == "production":
        raise RuntimeError(
            "REDIS_RESULT_URL or REDIS_URL is not configured. "
            "Required for imports Celery result backend."
        )

    warnings.warn(
        "REDIS_RESULT_URL not configured. Using development fallback (localhost/1).", RuntimeWarning
    )
    return "redis://localhost:6379/1"


REDIS_URL = _get_redis_url_for_imports()
REDIS_RESULT_URL = _get_redis_result_url()
RUNNER_MODE = os.getenv("IMPORTS_RUNNER_MODE", "celery")

celery_app = Celery(
    "gestiq_imports",
    broker=REDIS_URL,
    backend=REDIS_RESULT_URL,
    include=[
        "app.modules.imports.application.tasks.task_preprocess",
        "app.modules.imports.application.tasks.task_ocr",
        "app.modules.imports.application.tasks.task_classify",
        "app.modules.imports.application.tasks.task_extract",
        "app.modules.imports.application.tasks.task_validate",
        "app.modules.imports.application.tasks.task_publish",
        "app.modules.imports.application.tasks.task_import_file",
        "app.modules.imports.application.tasks.task_import_excel",  # Keep for backward compatibility
        "app.modules.imports.application.tasks.task_ocr_job",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    result_expires=int(os.getenv("CELERY_RESULT_EXPIRES", "3600")),
    task_ignore_result=os.getenv("CELERY_IGNORE_RESULT", "false").lower() == "true",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    task_default_retry_delay=30,
    task_max_retries=3,
    broker_connection_retry_on_startup=True,
    task_routes={
        "app.modules.imports.application.tasks.task_preprocess.*": {"queue": "imports_pre"},
        "app.modules.imports.application.tasks.task_ocr.*": {"queue": "imports_ocr"},
        "app.modules.imports.application.tasks.task_ocr_job.*": {"queue": "imports_ocr"},
        "app.modules.imports.application.tasks.task_classify.*": {"queue": "imports_ml"},
        "app.modules.imports.application.tasks.task_extract.*": {"queue": "imports_etl"},
        "app.modules.imports.application.tasks.task_validate.*": {"queue": "imports_val"},
        "app.modules.imports.application.tasks.task_publish.*": {"queue": "imports_pub"},
        # Route file imports to ETL queue
        "imports.import_file": {"queue": "imports_etl"},
        "imports.import_products_excel": {
            "queue": "imports_etl"
        },  # Keep for backward compatibility
    },
    task_queues=(
        Queue("imports_pre", routing_key="imports_pre"),
        Queue("imports_ocr", routing_key="imports_ocr"),
        Queue("imports_ml", routing_key="imports_ml"),
        Queue("imports_etl", routing_key="imports_etl"),
        Queue("imports_val", routing_key="imports_val"),
        Queue("imports_pub", routing_key="imports_pub"),
    ),
    task_annotations={
        "*": {
            "rate_limit": "50/m",
            "time_limit": 120,
            "soft_time_limit": 90,
        },
        "app.modules.imports.application.tasks.task_ocr.*": {
            "time_limit": 180,
            "soft_time_limit": 150,
        },
    },
)


def get_app() -> Celery:
    return celery_app
