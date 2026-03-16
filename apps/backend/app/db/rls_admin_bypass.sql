-- =============================================================================
-- RLS Admin Bypass — ejecutar UNA VEZ en producción
--
-- Agrega una política "admin_bypass" a TODAS las tablas que tengan RLS activo.
-- Los superadmins setean app.bypass_rls = 'true' via get_db() automáticamente,
-- lo que permite INSERT/UPDATE/DELETE/SELECT sin restricciones de tenant.
--
-- Requisito: ejecutar como el owner de las tablas o superuser.
-- =============================================================================

-- 1. Función helper reutilizable
CREATE OR REPLACE FUNCTION public.is_app_admin()
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
  SELECT current_setting('app.bypass_rls', true) = 'true'
$$;

-- 2. Agregar política de bypass a todas las tablas con RLS activo.
--    El bloque DO itera sobre pg_class para encontrarlas y aplica la política.
--    Si ya existe la policy "admin_bypass" en una tabla, la reemplaza.
DO $$
DECLARE
  r record;
BEGIN
  FOR r IN
    SELECT n.nspname AS schema_name, c.relname AS table_name
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relrowsecurity = true
      AND n.nspname = 'public'
      AND c.relkind = 'r'
    ORDER BY c.relname
  LOOP
    -- DROP primero para idempotencia
    EXECUTE format(
      'DROP POLICY IF EXISTS admin_bypass ON %I.%I',
      r.schema_name, r.table_name
    );
    EXECUTE format(
      'CREATE POLICY admin_bypass ON %I.%I FOR ALL '
      'USING (public.is_app_admin()) '
      'WITH CHECK (public.is_app_admin())',
      r.schema_name, r.table_name
    );
    RAISE NOTICE 'admin_bypass policy applied to %.%', r.schema_name, r.table_name;
  END LOOP;
END $$;
