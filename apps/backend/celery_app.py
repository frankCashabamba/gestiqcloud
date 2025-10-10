from __future__ import annotations

import os
from celery import Celery
from app.telemetry.otel import init_celery
from celery.schedules import crontab


def _redis_url() -> str:
    url = os.getenv("REDIS_URL") or "redis://localhost:6379/0"
    return url


celery_app = Celery(
    "gestiqcloud",
    broker=_redis_url(),
    backend=os.getenv("CELERY_RESULT_BACKEND", _redis_url()),
)

celery_app.conf.update(
    task_default_queue="default",
    task_queues={
        "sri": {},
        "sii": {},
        "default": {},
    },
    task_routes={
        "apps.backend.app.modules.einvoicing.tasks.sign_and_send": {"queue": "sri"},
        "apps.backend.app.modules.einvoicing.tasks.build_and_send_sii": {"queue": "sii"},
        "apps.backend.app.modules.einvoicing.tasks.scheduled_build_sii": {"queue": "sii"},
        "apps.backend.app.modules.einvoicing.tasks.scheduled_retry": {"queue": "sii"},
        "apps.backend.app.modules.webhooks.tasks.deliver": {"queue": "default"},
    },
)

# Optional: enable beat schedule when requested (pilot-safe)
if os.getenv("ENABLE_EINVOICING_BEAT", "0").lower() in ("1", "true", "yes"):
    # Default: run at 03:30 UTC daily
    celery_app.conf.beat_schedule = {
        "sii-build-daily": {
            "task": "apps.backend.app.modules.einvoicing.tasks.scheduled_build_sii",
            "schedule": crontab(minute=30, hour=3),
            # args determined inside task from env
        },
        "einvoicing-retry-15m": {
            "task": "apps.backend.app.modules.einvoicing.tasks.scheduled_retry",
            "schedule": crontab(minute="*/15"),
        },
    }

init_celery()
