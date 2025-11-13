"""
Sesión de base de datos y dependency injection
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import os

# Database URL
DATABASE_URL = os.getenv(
    "DB_DSN", "postgresql://postgres:root@localhost:5432/gestiqclouddb_dev"
)

# Engine
engine = create_engine(
    DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20, echo=False
)

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
