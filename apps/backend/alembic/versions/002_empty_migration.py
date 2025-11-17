"""Empty migration placeholder.

Revision ID: 002
Revises: 001_initial_schema
Create Date: 2025-11-17 00:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """No-op upgrade."""
    pass


def downgrade() -> None:
    """No-op downgrade."""
    pass
