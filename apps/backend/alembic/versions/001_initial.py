"""Initial migration - schema managed by SQLAlchemy models

Revision ID: 001_initial
Revises:
Create Date: 2025-11-17 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade: Schema created by SQLAlchemy models."""
    pass


def downgrade() -> None:
    """Downgrade: Not supported."""
    raise NotImplementedError("Downgrade not supported")
