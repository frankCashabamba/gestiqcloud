-- Add GUC-based bypass to empresa_must_have_user() trigger function
-- If app.disable_empresa_user_guard is set to '1' (or true/on), the check is skipped.

CREATE OR REPLACE FUNCTION public.empresa_must_have_user() RETURNS trigger AS $fn$
DECLARE
  v_disable text;
  v_count integer;
BEGIN
  -- Optional bypass for tests/dev via GUC
  BEGIN
    v_disable := current_setting('app.disable_empresa_user_guard', true);
  EXCEPTION WHEN OTHERS THEN
    v_disable := '';
  END;
  IF COALESCE(v_disable, '') IN ('1','true','TRUE','on','ON') THEN
    RETURN NEW;
  END IF;

  -- Original check: at least one UsuarioEmpresa per empresa
  SELECT COUNT(*) INTO v_count FROM public.usuarios_usuarioempresa u WHERE u.empresa_id = NEW.id;
  IF v_count < 1 THEN
    RAISE EXCEPTION 'empresa % must have at least one user', NEW.id USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END;
$fn$ LANGUAGE plpgsql;

-- Recreate trigger idempotently (in case it was dropped)
DROP TRIGGER IF EXISTS empresa_must_have_user_ct ON public.core_empresa;
CREATE CONSTRAINT TRIGGER empresa_must_have_user_ct
AFTER INSERT OR UPDATE OF id ON public.core_empresa
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION public.empresa_must_have_user();

