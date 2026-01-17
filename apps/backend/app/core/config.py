"""Core settings shim.

Public import point for settings: `from app.core.config import settings`.
Internally re-exports from legacy module to avoid churn.
"""

import logging
import os

logger = logging.getLogger(__name__)

try:
    from app.config.settings import settings as settings  # type: ignore
except Exception as e:  # pragma: no cover - keep imports resilient in CI
    # Provide a minimal fallback to avoid import-time crashes in tooling
    # This should only happen during testing or if settings are misconfigured
    logger.warning(
        "Failed to import main settings: %s. Using minimal fallback. "
        "This is only acceptable during testing or CI. "
        "In production, fix the settings import error.",
        e
    )
    
    class _SettingsFallback:  # noqa: D401 - simple fallback
        """Minimal settings fallback used only if real settings fail to import."""

        ENV = os.getenv("ENVIRONMENT", "development")
        # For fallback: accept empty CORS_ORIGINS in production (will fail validation elsewhere)
        # In development: allow localhost
        CORS_ORIGINS = (
            os.getenv("CORS_ORIGINS", "").split(",")
            if os.getenv("CORS_ORIGINS")
            else (
                ["http://localhost:8081", "http://localhost:8082"]
                if os.getenv("ENVIRONMENT", "development").lower() == "development"
                else []
            )
        )

    settings = _SettingsFallback()  # type: ignore
    logger.warning("⚠️  Using fallback settings. CORS validation may be incomplete.")
