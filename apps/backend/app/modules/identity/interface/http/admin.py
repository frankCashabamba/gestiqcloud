try:
    # Reuse existing router during migration
    from app.api.v1.admin.auth import router as router  # type: ignore
except Exception as _e:  # pragma: no cover - migration scaffold
    router = None  # noqa: F401

