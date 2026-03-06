from __future__ import annotations

from sqlalchemy.orm import Session


class SqlAlchemyRepo:
    """Minimal compatibility base for SQLAlchemy repositories."""

    def __init__(self, db: Session):
        self.db: Session = db
