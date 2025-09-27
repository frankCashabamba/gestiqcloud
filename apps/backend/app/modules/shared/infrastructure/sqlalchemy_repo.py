from __future__ import annotations

from sqlalchemy.orm import Session


class SqlAlchemyRepo:
    """Base repository for SQLAlchemy-backed repositories.

    Stores the `Session` as `self.db` and can be extended with common helpers.
    """

    def __init__(self, db: Session):
        self.db: Session = db

