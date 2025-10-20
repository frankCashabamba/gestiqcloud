-- Harden multitenancy defaults for usuarios_usuarioempresa
-- Ensures server-side DEFAULT from GUC and NOT NULL to avoid RLS violations

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'usuarios_usuarioempresa' AND column_name = 'tenant_id'
  ) THEN
    RAISE NOTICE 'Table public.usuarios_usuarioempresa.tenant_id not found; skipping';
  ELSE
    EXECUTE 'ALTER TABLE public.usuarios_usuarioempresa
              ALTER COLUMN tenant_id SET DEFAULT public.current_tenant()';
    BEGIN
      EXECUTE 'ALTER TABLE public.usuarios_usuarioempresa
                ALTER COLUMN tenant_id SET NOT NULL';
    EXCEPTION WHEN others THEN
      -- If existing NULLs prevent NOT NULL, log and skip; admins must backfill first
      RAISE NOTICE 'Skipping NOT NULL on usuarios_usuarioempresa.tenant_id; existing NULLs?';
    END;
  END IF;
END$$;
