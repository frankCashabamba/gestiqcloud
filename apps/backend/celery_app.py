from __future__ import annotations

import os

from celery import Celery
from celery.schedules import crontab

from app.telemetry.otel import init_celery


def _redis_url() -> str:
    """
    Get Redis URL from environment.
    
    In production, REDIS_URL is REQUIRED and must not point to localhost.
    In development, can fallback to localhost if explicitly set.
    """
    url = os.getenv("REDIS_URL", "").strip()
    
    if not url:
        import sys
        environment = os.getenv("ENVIRONMENT", "development").lower()
        
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
    
    # Validate no localhost in production
    if environment == "production" and ("localhost" in url or "127.0.0.1" in url):
        error_msg = f"REDIS_URL points to localhost in production: {url}"
        print(f"❌ CRITICAL: {error_msg}", file=sys.stderr)
        raise RuntimeError(error_msg)
    
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
