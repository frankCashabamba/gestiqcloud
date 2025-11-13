"""Central logging configuration for the backend.

Use `init_logging()` early (e.g., from main) if you need custom levels/formatters.
"""

import logging


def init_logging(level: int | None = None) -> None:
    logger = logging.getLogger()
    if level is None:
        level = logging.INFO
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)
        formatter = logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
