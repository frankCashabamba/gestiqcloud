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
    # SuperUser is a global table; ensure no RLS/indices reference tenant_id, then drop the column
    op.execute(
        """
        DO $$
        BEGIN
            -- Drop RLS policy if it was auto-created for tenant_id
            IF EXISTS (
                SELECT 1 FROM pg_policies
                 WHERE schemaname = 'public' AND tablename = 'auth_user' AND policyname = 'rls_tenant'
            ) THEN
                EXECUTE 'ALTER TABLE public.auth_user DISABLE ROW LEVEL SECURITY';
                EXECUTE 'DROP POLICY IF EXISTS rls_tenant ON public.auth_user';
            END IF;

            -- Drop index created by the generic RLS migration, if present
            IF EXISTS (
                SELECT 1 FROM pg_indexes
                 WHERE schemaname = 'public' AND tablename = 'auth_user' AND indexname = 'ix_auth_user_tenant_id'
            ) THEN
                EXECUTE 'DROP INDEX IF EXISTS public.ix_auth_user_tenant_id';
            END IF;
        END $$;
        """
    )

    op.execute("ALTER TABLE IF EXISTS auth_user DROP COLUMN IF EXISTS tenant_id")


def downgrade() -> None:
    # Restore column for backwards-compat if needed (nullable). RLS policy and index are not recreated automatically.
    op.execute("ALTER TABLE IF EXISTS auth_user ADD COLUMN IF NOT EXISTS tenant_id uuid NULL")
