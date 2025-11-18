"""Empty migration placeholder.

Revision ID: 005_pos_extensions
Revises: 004_config_tables
Create Date: 2025-11-17 00:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = "005_pos_extensions"
down_revision = "004_config_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """No-op upgrade."""
    pass


def downgrade() -> None:
    """No-op downgrade."""
    pass
