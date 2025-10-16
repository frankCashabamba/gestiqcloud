"""
Merge heads a20006_admin_migration_runs and a20030_superuser_drop_tenant

This is a no-op merge revision to linearize history and fix
"Multiple Alembic heads detected" in CI.

Revision ID: a20040_merge_heads
Revises: a20006_admin_migration_runs, a20030_superuser_drop_tenant
Create Date: 2025-10-16
"""

from alembic import op  # noqa: F401  (kept for symmetry with other revs)


# revision identifiers, used by Alembic.
revision = "a20040_merge_heads"
down_revision = ("a20006_admin_migration_runs", "a20030_superuser_drop_tenant")
branch_labels = None
depends_on = None


def upgrade() -> None:  # pragma: no cover - no-op merge
    pass


def downgrade() -> None:  # pragma: no cover - no-op merge
    pass

