-- Prevent deleting or demoting the last admin user of a company
-- Applies a DEFERRABLE constraint trigger on usuarios_usuarioempresa

DO $$
BEGIN
  -- Create function if not exists
  IF NOT EXISTS (
    SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE p.proname = 'forbid_remove_last_admin' AND n.nspname = 'public'
  ) THEN
    EXECUTE $$
      CREATE FUNCTION public.forbid_remove_last_admin() RETURNS trigger AS $$
      DECLARE
        v_count integer;
        v_empresa integer;
      BEGIN
        -- Determine empresa_id and whether the row after change is admin
        IF TG_OP = 'DELETE' THEN
          v_empresa := OLD.empresa_id;
          -- Count remaining admins excluding the row being deleted
          SELECT COUNT(*) INTO v_count
          FROM public.usuarios_usuarioempresa u
          WHERE u.empresa_id = v_empresa
            AND u.es_admin_empresa = true
            AND u.id <> OLD.id;
          IF v_count < 1 THEN
            RAISE EXCEPTION 'cannot remove last admin for company %', v_empresa USING ERRCODE = '23514';
          END IF;
          RETURN OLD;
        ELSIF TG_OP = 'UPDATE' THEN
          v_empresa := COALESCE(NEW.empresa_id, OLD.empresa_id);
          -- If we are demoting an admin to non-admin
          IF OLD.es_admin_empresa = true AND NEW.es_admin_empresa = false THEN
            SELECT COUNT(*) INTO v_count
            FROM public.usuarios_usuarioempresa u
            WHERE u.empresa_id = v_empresa
              AND u.es_admin_empresa = true
              AND u.id <> OLD.id;
            IF v_count < 1 THEN
              RAISE EXCEPTION 'cannot demote last admin for company %', v_empresa USING ERRCODE = '23514';
            END IF;
          END IF;
          RETURN NEW;
        END IF;
        RETURN NEW;
      END;
      $$ LANGUAGE plpgsql;
    $$;
  END IF;

  -- Drop existing trigger if present
  IF EXISTS (
    SELECT 1 FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE t.tgname = 'forbid_remove_last_admin_ct' AND c.relname = 'usuarios_usuarioempresa' AND n.nspname = 'public'
  ) THEN
    EXECUTE 'DROP TRIGGER forbid_remove_last_admin_ct ON public.usuarios_usuarioempresa';
  END IF;

  -- Create DEFERRABLE trigger so multi-row ops can add a new admin before removing the old in one transaction
  EXECUTE $$
    CREATE CONSTRAINT TRIGGER forbid_remove_last_admin_ct
    AFTER DELETE OR UPDATE OF es_admin_empresa ON public.usuarios_usuarioempresa
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW
    EXECUTE FUNCTION public.forbid_remove_last_admin();
  $$;
END$$;

