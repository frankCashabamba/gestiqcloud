try:
    from app.api.v1.tenant.auth import router as router  # type: ignore
except Exception as _e:  # pragma: no cover
    router = None  # noqa: F401

