"""
Sesión de base de datos y dependency injection
"""

import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


# Database URL - MUST be configured via DATABASE_URL or DB_DSN env var
# For migration scripts using DB_DSN, support both:
# - DATABASE_URL (preferred, used by FastAPI settings)
# - DB_DSN (legacy, for migration scripts)
def _get_database_url() -> str:
    """Get database URL from environment with proper fallback chain."""
    # Try DATABASE_URL first (standard variable)
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url

    # Fall back to DB_DSN (legacy, for systemd services)
    db_url = os.getenv("DB_DSN")
    if db_url:
        return db_url

    # No fallback to localhost - fail explicitly in production
    environment = os.getenv("ENVIRONMENT", "development").lower()
    if environment == "production":
        raise RuntimeError(
            "DATABASE_URL (or DB_DSN) is not configured. "
            "This is required in production. "
            "Example: DATABASE_URL=postgresql://user:pass@db.internal/gestiqcloud"
        )

    # Development fallback - use environment variable or fail with clear message
    import warnings

    dev_db_url = os.getenv("DEV_DATABASE_URL")
    if dev_db_url:
        warnings.warn("DATABASE_URL not set. Using DEV_DATABASE_URL fallback.", RuntimeWarning)
        return dev_db_url

    raise RuntimeError(
        "DATABASE_URL is not configured. "
        "For development, set DEV_DATABASE_URL or DATABASE_URL. "
        "Example: DATABASE_URL=postgresql://user:pass@localhost:5432/gestiqcloud_dev"
    )


DATABASE_URL = _get_database_url()

# Engine
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20, echo=False)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """
    Dependency para FastAPI

    Uso:
        @router.get("/")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager para workers Celery

    Uso:
        with get_db_context() as db:
            db.query(Model).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
