"""
Drop tenant_id from auth_user (SuperUser is global)

Revision ID: a20030_superuser_drop_tenant
Revises: a20020_rls_policies
Create Date: 2025-10-12
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "a20030_superuser_drop_tenant"
down_revision = "a20020_rls_policies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SuperUser is a global table; remove tenant_id if present
    op.execute("ALTER TABLE IF EXISTS auth_user DROP COLUMN IF EXISTS tenant_id")


def downgrade() -> None:
    # Restore column for backwards-compat if needed (nullable)
    op.execute("ALTER TABLE IF EXISTS auth_user ADD COLUMN IF NOT EXISTS tenant_id uuid NULL")

