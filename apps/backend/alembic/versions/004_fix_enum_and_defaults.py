"""Placeholder for ENUM and UUID column fixes.

Fixes are applied by migrate_all_migrations.py script.

Revision ID: 004_fix_enum_and_defaults
Revises: 003_core_business_tables
Create Date: 2025-11-19 00:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = "004_fix_enum_and_defaults"
down_revision = "003_core_business_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """No-op. Fixes applied by migrate_all_migrations.py."""
    pass


def downgrade() -> None:
    """No-op."""
    pass
