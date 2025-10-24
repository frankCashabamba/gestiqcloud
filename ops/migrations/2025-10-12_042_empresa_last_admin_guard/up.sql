-- Prevent deleting or demoting the last admin user of a company
-- Applies a DEFERRABLE constraint trigger on usuarios_usuarioempresa

-- Create or replace the guard function (idempotent)
CREATE OR REPLACE FUNCTION public.forbid_remove_last_admin() RETURNS trigger AS $fn$
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
$fn$ LANGUAGE plpgsql;

-- Recreate the constraint trigger (idempotent)
DROP TRIGGER IF EXISTS forbid_remove_last_admin_ct ON public.usuarios_usuarioempresa;
CREATE CONSTRAINT TRIGGER forbid_remove_last_admin_ct
AFTER DELETE OR UPDATE OF es_admin_empresa ON public.usuarios_usuarioempresa
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION public.forbid_remove_last_admin();
