-- Detach any trigger on auth_user that invokes function set_tenant_id()
DO $$
DECLARE
  trig RECORD;
BEGIN
  FOR trig IN
    SELECT t.tgname
    FROM pg_trigger t
    JOIN pg_class c ON c.oid = t.tgrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    JOIN pg_proc p ON p.oid = t.tgfoid
    WHERE n.nspname = 'public'
      AND c.relname = 'auth_user'
      AND NOT t.tgisinternal
      AND p.proname = 'set_tenant_id'
  LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS %I ON public.auth_user', trig.tgname);
  END LOOP;
END $$;

-- As a safeguard, disable RLS and drop any policies on auth_user (admin is global)
DO $$
DECLARE
  policy_name text;
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relname = 'auth_user'
  ) THEN
    EXECUTE 'ALTER TABLE public.auth_user DISABLE ROW LEVEL SECURITY';
    -- Drop any policy if present
    FOR policy_name IN SELECT policyname FROM pg_policies WHERE schemaname = 'public' AND tablename = 'auth_user'
    LOOP
      EXECUTE format('DROP POLICY IF EXISTS %I ON public.auth_user', policy_name);
    END LOOP;
  END IF;
END $$;
