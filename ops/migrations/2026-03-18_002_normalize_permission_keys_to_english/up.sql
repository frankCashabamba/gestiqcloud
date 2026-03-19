-- Normalize all permission keys from Spanish to canonical English
--
-- This migration renames legacy Spanish permission keys stored in
-- global_action_permissions to their English canonical form, matching
-- the module IDs already normalized in 2026-02-14_005.
--
-- Affected mappings:
--   usuarios.*    → users.*
--   produccion.*  → production.*
--   facturacion.* → billing.*
--   clientes.*    → customers.*
--   finanzas.*    → finances.*
--   rrhh.*        → hr.*
--   reportes.*    → reports.*

-- 1. global_action_permissions table
UPDATE global_action_permissions SET key = REPLACE(key, 'usuarios:', 'users:'),        module = 'users'       WHERE key LIKE 'usuarios:%';
UPDATE global_action_permissions SET key = REPLACE(key, 'produccion:', 'production:'),  module = 'production'  WHERE key LIKE 'produccion:%';
UPDATE global_action_permissions SET key = REPLACE(key, 'facturacion:', 'billing:'),    module = 'billing'     WHERE key LIKE 'facturacion:%';
UPDATE global_action_permissions SET key = REPLACE(key, 'clientes:', 'customers:'),    module = 'customers'   WHERE key LIKE 'clientes:%';
UPDATE global_action_permissions SET key = REPLACE(key, 'finanzas:', 'finances:'),     module = 'finances'    WHERE key LIKE 'finanzas:%';
UPDATE global_action_permissions SET key = REPLACE(key, 'rrhh:', 'hr:'),               module = 'hr'          WHERE key LIKE 'rrhh:%';
UPDATE global_action_permissions SET key = REPLACE(key, 'reportes:', 'reports:'),      module = 'reports'     WHERE key LIKE 'reportes:%';

-- Also fix dot-separated keys (produccion.read → production.read)
UPDATE global_action_permissions SET key = REPLACE(key, 'usuarios.', 'users.'),        module = 'users'       WHERE key LIKE 'usuarios.%';
UPDATE global_action_permissions SET key = REPLACE(key, 'produccion.', 'production.'),  module = 'production'  WHERE key LIKE 'produccion.%';
UPDATE global_action_permissions SET key = REPLACE(key, 'facturacion.', 'billing.'),    module = 'billing'     WHERE key LIKE 'facturacion.%';
UPDATE global_action_permissions SET key = REPLACE(key, 'clientes.', 'customers.'),    module = 'customers'   WHERE key LIKE 'clientes.%';
UPDATE global_action_permissions SET key = REPLACE(key, 'finanzas.', 'finances.'),     module = 'finances'    WHERE key LIKE 'finanzas.%';
UPDATE global_action_permissions SET key = REPLACE(key, 'rrhh.', 'hr.'),               module = 'hr'          WHERE key LIKE 'rrhh.%';
UPDATE global_action_permissions SET key = REPLACE(key, 'reportes.', 'reports.'),      module = 'reports'     WHERE key LIKE 'reportes.%';

-- 2. Normalize keys stored inside company_roles.permissions JSON
--    This updates the top-level keys of the JSON permission dicts
--    e.g. {"usuarios": {"create": true}} → {"users": {"create": true}}
UPDATE company_roles
SET permissions = (
  SELECT json_object_agg(
    CASE key
      WHEN 'usuarios'    THEN 'users'
      WHEN 'produccion'  THEN 'production'
      WHEN 'facturacion' THEN 'billing'
      WHEN 'clientes'    THEN 'customers'
      WHEN 'finanzas'    THEN 'finances'
      WHEN 'rrhh'        THEN 'hr'
      WHEN 'reportes'    THEN 'reports'
      ELSE key
    END,
    value
  )
  FROM json_each(permissions)
)
WHERE permissions IS NOT NULL
  AND permissions::text ~ '"(usuarios|produccion|facturacion|clientes|finanzas|rrhh|reportes)"';
