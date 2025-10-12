-- Constraint trigger to prevent committing an empresa without at least one user
-- This enforces the invariant: every empresa must have a principal user (at least one UsuarioEmpresa row)

DO $$
BEGIN
  -- Create the validation function if not exists
  IF NOT EXISTS (
    SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
     WHERE p.proname = 'empresa_must_have_user' AND n.nspname = 'public'
  ) THEN
    EXECUTE $$
    CREATE FUNCTION public.empresa_must_have_user() RETURNS trigger AS $$
    DECLARE
      v_count integer;
    BEGIN
      -- Check for at least one UsuarioEmpresa per empresa
      SELECT COUNT(*) INTO v_count FROM public.usuarios_usuarioempresa u WHERE u.empresa_id = NEW.id;
      IF v_count < 1 THEN
        RAISE EXCEPTION 'empresa % must have at least one user' USING ERRCODE = '23514';
      END IF;
      RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    $$;
  END IF;

  -- Drop and recreate the constraint trigger (deferrable) to ensure it runs at end of transaction
  IF EXISTS (
    SELECT 1 FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE t.tgname = 'empresa_must_have_user_ct' AND c.relname = 'core_empresa' AND n.nspname = 'public'
  ) THEN
    EXECUTE 'DROP TRIGGER empresa_must_have_user_ct ON public.core_empresa';
  END IF;

  -- DEFERRABLE INITIALLY DEFERRED so multi-step inserts in one transaction are allowed
  EXECUTE $$
    CREATE CONSTRAINT TRIGGER empresa_must_have_user_ct
    AFTER INSERT OR UPDATE OF id ON public.core_empresa
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW
    EXECUTE FUNCTION public.empresa_must_have_user();
  $$;
END$$;

