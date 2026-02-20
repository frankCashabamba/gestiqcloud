"""Celery app para procesamiento asíncrono de imports."""

from __future__ import annotations

import os
import warnings

from celery import Celery
from kombu import Queue

from app.config import env_loader as _env_loader  # noqa: F401


def _get_redis_url_for_imports() -> str:
    """
    Get Redis URL for imports Celery broker with validation.

    In production: REDIS_URL is required.
    In development: REDIS_URL or DEV_REDIS_URL is required.
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

    dev_redis_url = os.getenv("DEV_REDIS_URL", "").strip()
    if dev_redis_url:
        warnings.warn(
            "REDIS_URL not configured. Using DEV_REDIS_URL for development.",
            RuntimeWarning,
        )
        return dev_redis_url

    raise RuntimeError(
        "REDIS_URL is not configured. "
        "Set REDIS_URL (all environments) or DEV_REDIS_URL (development only)."
    )


def _get_redis_result_url() -> str:
    """Get Redis URL for Celery result backend with validation."""
    # Try REDIS_RESULT_URL first
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

    # Development-specific explicit result URL
    dev_redis_result_url = os.getenv("DEV_REDIS_RESULT_URL", "").strip()
    if dev_redis_result_url:
        warnings.warn(
            "REDIS_RESULT_URL not configured. Using DEV_REDIS_RESULT_URL for development.",
            RuntimeWarning,
        )
        return dev_redis_result_url

    # Fallback to DEV_REDIS_URL in development
    dev_redis_url = os.getenv("DEV_REDIS_URL", "").strip()
    if dev_redis_url:
        warnings.warn(
            "REDIS_RESULT_URL not configured. Deriving from DEV_REDIS_URL for development.",
            RuntimeWarning,
        )
        if dev_redis_url.endswith("/0"):
            return dev_redis_url[:-1] + "1"
        return dev_redis_url

    environment = os.getenv("ENVIRONMENT", "development").lower()
    if environment == "production":
        raise RuntimeError(
            "REDIS_RESULT_URL or REDIS_URL is not configured. "
            "Required for imports Celery result backend."
        )

    raise RuntimeError(
        "REDIS_RESULT_URL is not configured. "
        "Set REDIS_RESULT_URL/REDIS_URL (all environments) or "
        "DEV_REDIS_RESULT_URL/DEV_REDIS_URL (development only)."
    )


REDIS_URL = _get_redis_url_for_imports()
REDIS_RESULT_URL = _get_redis_result_url()
RUNNER_MODE = os.getenv("IMPORTS_RUNNER_MODE", "celery")
IMPORTS_WORKER_PROFILE = os.getenv("IMPORTS_WORKER_PROFILE", "clean").strip().lower()


def _get_task_includes() -> list[str]:
    """Celery task includes by worker profile.

    - clean: only new pipeline/core tasks (no legacy OCR/extract tasks)
    - legacy: includes old task_ocr/task_extract modules
    """
    core = [
        "app.modules.imports.application.tasks.task_preprocess",
        "app.modules.imports.application.tasks.task_classify",
        "app.modules.imports.application.tasks.task_validate",
        "app.modules.imports.application.tasks.task_publish",
        "app.modules.imports.application.tasks.task_import_file",
        "app.modules.imports.application.tasks.task_import_excel",  # backward compatibility
        "app.modules.imports.application.tasks.task_ocr_job",
    ]
    if IMPORTS_WORKER_PROFILE == "legacy":
        core.insert(1, "app.modules.imports.application.tasks.task_ocr")
        core.insert(3, "app.modules.imports.application.tasks.task_extract")
    return core


celery_app = Celery(
    "gestiq_imports",
    broker=REDIS_URL,
    backend=REDIS_RESULT_URL,
    include=_get_task_includes(),
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
