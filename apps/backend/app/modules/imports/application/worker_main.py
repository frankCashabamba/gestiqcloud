"""Worker entry point para imports con tenant context."""

from __future__ import annotations

import logging
import signal
import sys
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

    argv = [
        "worker",
        "--loglevel=info",
        "--concurrency=4",
        "-Q",
        "imports_pre,imports_ocr,imports_ml,imports_etl,imports_val,imports_pub",
        "-n",
        "imports-worker@%h",
    ]

    celery_app.worker_main(argv)
