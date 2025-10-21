-- Restore tenant awareness on auth_user (not recommended for production)
DO $$
BEGIN
  -- Add tenant_id back if missing
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='auth_user' AND column_name='tenant_id'
  ) THEN
    EXECUTE 'ALTER TABLE public.auth_user ADD COLUMN tenant_id uuid NULL';
  END IF;

  -- Recreate index if missing
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND tablename = 'auth_user' AND indexname = 'ix_auth_user_tenant_id'
  ) THEN
    EXECUTE 'CREATE INDEX ix_auth_user_tenant_id ON public.auth_user (tenant_id)';
  END IF;

  -- Enable RLS and recreate policy
  EXECUTE 'ALTER TABLE public.auth_user ENABLE ROW LEVEL SECURITY';
  EXECUTE 'ALTER TABLE public.auth_user FORCE ROW LEVEL SECURITY';
  -- Drop existing policy if present
  IF EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'auth_user' AND policyname = 'rls_tenant'
  ) THEN
    EXECUTE 'DROP POLICY rls_tenant ON public.auth_user';
  END IF;
  EXECUTE $$CREATE POLICY rls_tenant ON public.auth_user
           USING (tenant_id::text = current_setting('app.tenant_id', true))
           WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true))$$;
END $$;

