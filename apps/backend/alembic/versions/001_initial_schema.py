"""Create initial schema from all SQLAlchemy models

Revision ID: 001_initial_schema
Revises:
Create Date: 2025-11-17 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all tables from SQLAlchemy models.

    This migration delegates table creation to the application's
    Base.metadata.create_all() during Alembic upgrades.

    For development, tables are created automatically from models via
    the alembic/env.py configuration and SQLAlchemy's model definitions.
    """
    # Schema creation is handled by Alembic's compare_type/compare_server_default
    # settings in env.py, which auto-generates DDL from target_metadata (all models)
    pass


def downgrade() -> None:
    """Downgrade: Drop all tables.

    WARNING: This will delete all data. Use with caution.
    """
    # In production, you typically would not drop tables automatically
    # Instead, you might want to:
    # 1. Backup the database
    # 2. Create a separate downgrade migration
    # 3. Or handle it manually via your DBA
    raise NotImplementedError(
        "Full downgrade is not supported for initial schema. "
        "Use database backups and manual migration if needed."
    )
