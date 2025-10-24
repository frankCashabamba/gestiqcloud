-- Make auth_user a global admin table (no tenant_id, no RLS)
DO $$
BEGIN
  -- Drop RLS policy if present
  IF EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'auth_user' AND policyname = 'rls_tenant'
  ) THEN
    EXECUTE 'DROP POLICY rls_tenant ON public.auth_user';
  END IF;

  -- Disable RLS if enabled
  IF EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    JOIN pg_catalog.pg_class rel ON c.oid = rel.oid
    WHERE n.nspname = 'public' AND c.relname = 'auth_user'
  ) THEN
    EXECUTE 'ALTER TABLE public.auth_user DISABLE ROW LEVEL SECURITY';
  END IF;

  -- Drop index on tenant_id if exists
  IF EXISTS (
    SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND tablename = 'auth_user' AND indexname = 'ix_auth_user_tenant_id'
  ) THEN
    EXECUTE 'DROP INDEX public.ix_auth_user_tenant_id';
  END IF;

  -- Drop tenant_id column if exists
  IF EXISTS (
    SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='auth_user' AND column_name='tenant_id'
  ) THEN
    EXECUTE 'ALTER TABLE public.auth_user DROP COLUMN tenant_id';
  END IF;
END $$;

