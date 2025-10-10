from __future__ import annotations

import os
from celery import Celery


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
    },
)

