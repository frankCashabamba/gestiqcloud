"""
Bootstrap all ORM tables using SQLAlchemy Base.metadata

Revision ID: a00000_orm_bootstrap
Revises: 
Create Date: 2025-10-05
"""

from alembic import op
import importlib
import pkgutil
from typing import Iterable


# revision identifiers, used by Alembic.
revision = "a00000_orm_bootstrap"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create all ORM-declared tables. This is a one-time baseline.
    try:
        from app.config.database import Base, engine
    except Exception:
        from apps.backend.app.config.database import Base, engine  # type: ignore
    
    # Discover and import all model modules so classes register on Base
    def _import_all(prefix: str, package_name: str) -> None:
        try:
            pkg = importlib.import_module(package_name)
            if not hasattr(pkg, "__path__"):
                return
            for m in pkgutil.walk_packages(pkg.__path__, prefix=prefix):
                modname = m.name
                try:
                    importlib.import_module(modname)
                except Exception:
                    # Best-effort: some modules may require optional deps
                    pass
        except Exception:
            pass

    # Import app models and infrastructure models under modules/*
    _import_all("app.models.", "app.models")
    _import_all("apps.backend.app.models.", "apps.backend.app.models")
    _import_all("app.modules.", "app.modules")
    _import_all("apps.backend.app.modules.", "apps.backend.app.modules")

    # Important: run once on empty DBs to establish baseline schema
    Base.metadata.create_all(bind=engine)


def downgrade() -> None:
    # Do not drop all tables; baseline migration is not reversible safely.
    pass
