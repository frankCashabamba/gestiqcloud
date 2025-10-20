-- Apply tenant-based RLS across all tables with a tenant_id column.
-- This migration is idempotent and can be re-run safely.

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

    -- Drop/Create single tenant policy
    EXECUTE format('DROP POLICY IF EXISTS rls_tenant ON %I.%I', r.table_schema, r.table_name);
    EXECUTE format(
      'CREATE POLICY rls_tenant ON %I.%I USING (tenant_id::text = current_setting(''app.tenant_id'', true)) WITH CHECK (tenant_id::text = current_setting(''app.tenant_id'', true))',
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

    -- Optional: set DEFAULT tenant_id := current_tenant() when no default is set
    SELECT (column_default IS NOT NULL) INTO has_default
    FROM information_schema.columns
    WHERE table_schema = r.table_schema AND table_name = r.table_name AND column_name = 'tenant_id';
    IF NOT has_default THEN
      EXECUTE format('ALTER TABLE %I.%I ALTER COLUMN tenant_id SET DEFAULT public.current_tenant()', r.table_schema, r.table_name);
    END IF;
  END LOOP;
END $$;
