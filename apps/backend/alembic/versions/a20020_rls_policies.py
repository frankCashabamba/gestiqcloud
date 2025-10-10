"""
Apply tenant-based RLS policies idempotently to all tables with tenant_id

Revision ID: a20020_rls_policies
Revises: a20010_bootstrap_structs
Create Date: 2025-10-10
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "a20020_rls_policies"
down_revision = "a20010_bootstrap_structs"
branch_labels = None
depends_on = None


def upgrade() -> None:  # pragma: no cover - DDL heavy
    op.execute(
        """
        -- Helper: current_tenant() returns UUID from session GUC
        CREATE OR REPLACE FUNCTION public.current_tenant() RETURNS uuid
        LANGUAGE sql STABLE AS $$
          SELECT current_setting('app.tenant_id', true)::uuid
        $$;

        DO $$
        DECLARE
          r RECORD;
          ix_name text;
          has_default boolean;
        BEGIN
          FOR r IN
            SELECT c.table_schema, c.table_name
            FROM information_schema.columns c
            WHERE c.column_name = 'tenant_id'
              AND c.table_schema NOT IN ('pg_catalog','information_schema')
            GROUP BY c.table_schema, c.table_name
            ORDER BY c.table_schema, c.table_name
          LOOP
            -- Enable + Force RLS
            EXECUTE format('ALTER TABLE %I.%I ENABLE ROW LEVEL SECURITY', r.table_schema, r.table_name);
            EXECUTE format('ALTER TABLE %I.%I FORCE ROW LEVEL SECURITY', r.table_schema, r.table_name);

            -- Recreate single tenant policy
            EXECUTE format('DROP POLICY IF EXISTS rls_tenant ON %I.%I', r.table_schema, r.table_name);
            EXECUTE format(
              'CREATE POLICY rls_tenant ON %I.%I USING (tenant_id = current_setting(''app.tenant_id'', true)::uuid) WITH CHECK (tenant_id = current_setting(''app.tenant_id'', true)::uuid)',
              r.table_schema, r.table_name
            );

            -- Ensure index on tenant_id
            ix_name := format('ix_%s_tenant_id', r.table_name);
            IF NOT EXISTS (
              SELECT 1 FROM pg_indexes
              WHERE schemaname = r.table_schema AND tablename = r.table_name AND indexname = ix_name
            ) THEN
              EXECUTE format('CREATE INDEX %I ON %I.%I (tenant_id)', ix_name, r.table_schema, r.table_name);
            END IF;

            -- Optional: set DEFAULT tenant_id := current_tenant() when no default present
            SELECT (column_default IS NOT NULL) INTO has_default
            FROM information_schema.columns
            WHERE table_schema = r.table_schema AND table_name = r.table_name AND column_name = 'tenant_id';
            IF NOT has_default THEN
              EXECUTE format('ALTER TABLE %I.%I ALTER COLUMN tenant_id SET DEFAULT public.current_tenant()', r.table_schema, r.table_name);
            END IF;
          END LOOP;
        END $$;
        """
    )


def downgrade() -> None:  # pragma: no cover - we keep RLS enforced
    pass

