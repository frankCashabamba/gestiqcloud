from __future__ import annotations

import os
import sys

from celery import Celery
from celery.schedules import crontab

try:
    from app.config import env_loader as _env_loader  # noqa: F401
    from app.telemetry.otel import init_celery
except ImportError:
    from apps.backend.app.config import env_loader as _env_loader  # noqa: F401
    from apps.backend.app.telemetry.otel import init_celery


def _redis_url() -> str:
    """
    Get Redis URL from environment.

    In production, REDIS_URL is REQUIRED and must not point to localhost.
    In development, can fallback to localhost if explicitly set.
    """
    environment = os.getenv("ENVIRONMENT", "development").lower()
    url = os.getenv("REDIS_URL", "").strip()

    if not url:
        if environment == "production":
            error_msg = (
                "REDIS_URL is not configured. Required in production.\n"
                "Set REDIS_URL environment variable (e.g., redis://cache.internal:6379/1)"
            )
            print(f"❌ CRITICAL: {error_msg}", file=sys.stderr)
            raise RuntimeError(error_msg)

        # In development, require explicit DEV_REDIS_URL or fail
        dev_redis_url = os.getenv("DEV_REDIS_URL")
        if dev_redis_url:
            print("⚠️  REDIS_URL not set, using DEV_REDIS_URL fallback", file=sys.stderr)
            url = dev_redis_url
        else:
            error_msg = (
                "REDIS_URL is not configured. "
                "For development, set DEV_REDIS_URL or REDIS_URL. "
                "Example: REDIS_URL=redis://localhost:6379/0"
            )
            print(f"❌ ERROR: {error_msg}", file=sys.stderr)
            raise RuntimeError(error_msg)

    # Validate no localhost in production (unless explicitly allowed for single-server deploys)
    if environment == "production" and ("localhost" in url or "127.0.0.1" in url):
        if os.getenv("ALLOW_LOCAL_REDIS_IN_PROD", "").lower() in ("1", "true", "yes"):
            print("⚠️  REDIS_URL points to localhost in production (allowed via ALLOW_LOCAL_REDIS_IN_PROD)", file=sys.stderr)
        else:
            error_msg = f"REDIS_URL points to localhost in production: {url}"
            print(f"❌ CRITICAL: {error_msg}", file=sys.stderr)
            raise RuntimeError(error_msg)

    return url


_REDIS_URL = _redis_url()

celery_app = Celery(
    "gestiqcloud",
    broker=_REDIS_URL,
    backend=os.getenv("CELERY_RESULT_BACKEND", _REDIS_URL),
)

sys.modules.setdefault("app.celery_app", sys.modules[__name__])
sys.modules.setdefault("apps.backend.celery_app", sys.modules[__name__])

_on_windows = sys.platform == "win32"
_celery_pool = os.getenv("CELERY_POOL", "solo" if _on_windows else "prefork")

celery_app.conf.update(
    # En Windows, billiard no puede crear semáforos de sistema → usar pool solo
    worker_pool=_celery_pool,
    task_default_queue="default",
    task_queues={
        "sri": {},
        "sii": {},
        "default": {},
        "importador": {},
    },
    task_routes={
        "apps.backend.app.modules.einvoicing.tasks.sign_and_send": {"queue": "sri"},
        "apps.backend.app.modules.einvoicing.tasks.build_and_send_sii": {"queue": "sii"},
        "apps.backend.app.modules.einvoicing.tasks.scheduled_build_sii": {"queue": "sii"},
        "apps.backend.app.modules.einvoicing.tasks.scheduled_retry": {"queue": "sii"},
        "apps.backend.app.modules.webhooks.tasks.deliver": {"queue": "default"},
        "importador.process_document": {"queue": "importador"},
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

# Import task modules after Celery app creation so task decorators register them.
for _task_module in (
    "app.modules.importador.tasks",
    "apps.backend.app.modules.importador.tasks",
):
    try:
        __import__(_task_module)
        break
    except Exception:
        continue

init_celery()
