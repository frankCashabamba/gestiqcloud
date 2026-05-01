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


def _is_testing_environment() -> bool:
    """
    Detect if we're running in a test environment.

    Uses multiple indicators for robustness:
    - TESTING environment variable
    - PYTEST_CURRENT_TEST (set by pytest during test runs)
    """
    return (
        os.getenv("TESTING") == "1" or
        os.getenv("PYTEST_CURRENT_TEST") is not None
    )


def _get_redis_url() -> str:
    """
    Get Redis URL from environment.

    In testing, uses in-memory broker to avoid external dependencies.
    In production, REDIS_URL is REQUIRED and must not point to localhost.
    In development, can fallback to localhost if explicitly set.
    """
    # Use in-memory broker for testing
    if _is_testing_environment():
        return "memory://"

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


# Global variable to hold the Celery app instance
# Initialized lazily to avoid import-time side effects
_celery_app: Celery | None = None


def create_celery_app() -> Celery:
    """
    Create and configure the Celery application.

    This function centralizes Celery initialization and handles environment-specific
    configuration. It's called lazily to avoid import-time side effects.
    """
    global _celery_app

    if _celery_app is not None:
        return _celery_app

    redis_url = _get_redis_url()

    # For testing, use cache+memory backend instead of Redis
    if _is_testing_environment():
        result_backend = "cache+memory://"
    else:
        result_backend = os.getenv("CELERY_RESULT_BACKEND", redis_url)

    _celery_app = Celery(
        "gestiqcloud",
        broker=redis_url,
        backend=result_backend,
    )

    sys.modules.setdefault("app.celery_app", sys.modules[__name__])
    sys.modules.setdefault("apps.backend.celery_app", sys.modules[__name__])

    _on_windows = sys.platform == "win32"
    _celery_pool = os.getenv("CELERY_POOL", "solo" if _on_windows else "prefork")

    # Base configuration
    base_config = {
        # En Windows, billiard no puede crear semáforos de sistema → usar pool solo
        "worker_pool": _celery_pool,
        "task_default_queue": "default",
        "task_queues": {
            "sri": {},
            "sii": {},
            "default": {},
            "importador": {},
        },
        "task_routes": {
            "apps.backend.app.modules.einvoicing.tasks.sign_and_send": {"queue": "sri"},
            "apps.backend.app.modules.einvoicing.tasks.build_and_send_sii": {"queue": "sii"},
            "apps.backend.app.modules.einvoicing.tasks.scheduled_build_sii": {"queue": "sii"},
            "apps.backend.app.modules.einvoicing.tasks.scheduled_retry": {"queue": "sii"},
            "apps.backend.app.modules.webhooks.tasks.deliver": {"queue": "default"},
            "importador.process_document": {"queue": "importador"},
        },
    }

    # Testing-specific configuration
    if _is_testing_environment():
        test_config = {
            "task_always_eager": True,
            "task_eager_propagates": True,
            "result_expires": 0,
            "result_backend_transport_options": {"master_name": "mymaster"},
        }
        base_config.update(test_config)

    _celery_app.conf.update(base_config)

    # Optional: enable beat schedule when requested (pilot-safe)
    beat_schedule: dict = {}
    if os.getenv("ENABLE_EINVOICING_BEAT", "0").lower() in ("1", "true", "yes"):
        # Default: run at 03:30 UTC daily
        beat_schedule.update({
            "sii-build-daily": {
                "task": "apps.backend.app.modules.einvoicing.tasks.scheduled_build_sii",
                "schedule": crontab(minute=30, hour=3),
                # args determined inside task from env
            },
            "einvoicing-retry-15m": {
                "task": "apps.backend.app.modules.einvoicing.tasks.scheduled_retry",
                "schedule": crontab(minute="*/15"),
            },
        })

    # Reports scheduler — gated por REPORTS_SCHEDULER_ENABLED.
    # Si está deshabilitado, las tareas siguen siendo invocables manualmente
    # (están registradas en apps.backend.app.workers.reports_tasks) pero no
    # se programan en beat.
    if os.getenv("REPORTS_SCHEDULER_ENABLED", "0").lower() in ("1", "true", "yes"):
        beat_schedule.update({
            "process-scheduled-reports": {
                "task": "apps.backend.app.workers.reports_tasks.process_due_scheduled_reports",
                "schedule": crontab(minute="*/5"),
            },
            "recalculate-profit-snapshots-nightly": {
                "task": "apps.backend.app.workers.reports_tasks.recalculate_profit_snapshots",
                "schedule": crontab(minute=0, hour=3),
            },
        })

    if beat_schedule:
        _celery_app.conf.beat_schedule = beat_schedule

    # Initialize telemetry
    try:
        init_celery()
    except Exception as e:
        # Don't fail completely if telemetry initialization fails
        print(f"⚠️  Warning: Failed to initialize Celery telemetry: {e}", file=sys.stderr)

    return _celery_app


def get_celery_app() -> Celery:
    """
    Get the Celery application instance.

    This is the preferred way to access the Celery app throughout the codebase.
    It ensures lazy initialization and avoids import-time side effects.
    """
    if _celery_app is None:
        return create_celery_app()
    return _celery_app


# Legacy compatibility - expose celery_app as a property-like accessor
# This maintains backward compatibility while avoiding import-time initialization
class _CeleryAppProxy:
    """Proxy object that lazily initializes the Celery app when accessed."""

    def __getattr__(self, name):
        celery_app = get_celery_app()
        return getattr(celery_app, name)

    def __call__(self, *args, **kwargs):
        celery_app = get_celery_app()
        return celery_app(*args, **kwargs)


# Create a proxy that looks like the old celery_app module variable
celery_app = _CeleryAppProxy()


# Import task modules after Celery app creation so task decorators register them.
# This is done lazily to avoid import-time side effects.
def _import_task_modules():
    """Import task modules to register Celery tasks."""
    for task_module in (
        "app.modules.importador.tasks",
        "apps.backend.app.modules.importador.tasks",
    ):
        try:
            __import__(task_module)
            break
        except Exception:
            continue

    for task_module in (
        "app.workers.einvoicing_tasks",
        "apps.backend.app.workers.einvoicing_tasks",
    ):
        try:
            __import__(task_module)
            break
        except Exception:
            continue

    for task_module in (
        "app.workers.reports_tasks",
        "apps.backend.app.workers.reports_tasks",
    ):
        try:
            __import__(task_module)
            break
        except Exception:
            continue

# Auto-import task modules when the app is created
# This ensures tasks are registered in production/development
if not _is_testing_environment():
    _import_task_modules()
