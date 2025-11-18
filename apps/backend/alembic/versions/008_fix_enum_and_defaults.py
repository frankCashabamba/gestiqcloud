"""Placeholder for ENUM and UUID column fixes.

Fixes are applied by migrate_all_migrations.py script.

Revision ID: 008_fix_enum_and_defaults
Revises: 006_einvoicing_tables
Create Date: 2025-11-19 00:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = "008_fix_enum_and_defaults"
down_revision = "006_einvoicing_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """No-op. Fixes applied by migrate_all_migrations.py."""
    pass


def downgrade() -> None:
    """No-op."""
    pass
