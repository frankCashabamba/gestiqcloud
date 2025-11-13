"""Celery app para procesamiento asíncrono de imports."""

from __future__ import annotations

import os

from celery import Celery
from kombu import Queue

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
RUNNER_MODE = os.getenv("IMPORTS_RUNNER_MODE", "celery")

celery_app = Celery(
    "gestiq_imports",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "app.modules.imports.application.tasks.task_preprocess",
        "app.modules.imports.application.tasks.task_ocr",
        "app.modules.imports.application.tasks.task_classify",
        "app.modules.imports.application.tasks.task_extract",
        "app.modules.imports.application.tasks.task_validate",
        "app.modules.imports.application.tasks.task_publish",
        "app.modules.imports.application.tasks.task_import_file",
        "app.modules.imports.application.tasks.task_import_excel",  # Keep for backward compatibility
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
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
