"""Core DB shim.

Public import point for SQLAlchemy session/engine/base.
"""

try:
    from app.config.database import Base, SessionLocal, engine  # type: ignore
except Exception:  # pragma: no cover
    # Provide very light fallbacks to avoid import errors in analysis contexts
    SessionLocal = None  # type: ignore
    engine = None  # type: ignore

    class _Base:  # noqa: D401
        """Placeholder Base"""

        metadata = None

    Base = _Base()  # type: ignore

__all__ = ["SessionLocal", "engine", "Base"]
