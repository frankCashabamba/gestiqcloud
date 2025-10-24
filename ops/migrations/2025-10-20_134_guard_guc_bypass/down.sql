-- Restore the original empresa_must_have_user() function without GUC bypass

CREATE OR REPLACE FUNCTION public.empresa_must_have_user() RETURNS trigger AS $fn$
DECLARE
  v_count integer;
BEGIN
  SELECT COUNT(*) INTO v_count FROM public.usuarios_usuarioempresa u WHERE u.empresa_id = NEW.id;
  IF v_count < 1 THEN
    RAISE EXCEPTION 'empresa % must have at least one user', NEW.id USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END;
$fn$ LANGUAGE plpgsql;

-- Ensure trigger exists
DROP TRIGGER IF EXISTS empresa_must_have_user_ct ON public.core_empresa;
CREATE CONSTRAINT TRIGGER empresa_must_have_user_ct
AFTER INSERT OR UPDATE OF id ON public.core_empresa
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION public.empresa_must_have_user();

