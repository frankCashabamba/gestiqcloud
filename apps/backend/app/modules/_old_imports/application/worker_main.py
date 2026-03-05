"""Worker entry point para imports con tenant context."""

from __future__ import annotations

import logging
import signal
import sys

from app.config import env_loader as _env_loader  # noqa: F401
from app.modules.imports.application.celery_app import celery_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


def handle_shutdown(signum, frame):
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    celery_app.control.shutdown()
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    logger.info("Starting GestiQ Imports worker...")

    is_windows = sys.platform.startswith("win")
    argv = [
        "worker",
        "--loglevel=info",
        "-Q",
        "imports_pre,imports_ocr,imports_ml,imports_etl,imports_val,imports_pub",
        "-n",
        "imports-worker@%h",
    ]

    if is_windows:
        # billiard/prefork is unstable on Windows (WinError 5/6 in child workers).
        # Use solo pool for local development stability.
        argv.extend(["--pool=solo", "--concurrency=1"])
        logger.info("Windows detected: starting Celery imports worker with pool=solo")
    else:
        argv.extend(["--concurrency=4"])

    celery_app.worker_main(argv)
