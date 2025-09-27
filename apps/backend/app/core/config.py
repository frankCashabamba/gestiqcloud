"""Core settings shim.

Public import point for settings: `from app.core.config import settings`.
Internally re-exports from legacy module to avoid churn.
"""

try:
    from app.config.settings import settings as settings  # type: ignore
except Exception:  # pragma: no cover - keep imports resilient in CI
    # Provide a minimal fallback to avoid import-time crashes in tooling
    class _SettingsFallback:  # noqa: D401 - simple fallback
        """Minimal settings fallback used only if real settings fail to import."""

        ENV = "development"
        CORS_ORIGINS = ["http://localhost:8081", "http://localhost:8082"]

    settings = _SettingsFallback()  # type: ignore

