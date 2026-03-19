-- Revert English permission keys back to Spanish
-- (reverse of up.sql)

UPDATE global_action_permissions SET key = REPLACE(key, 'users:', 'usuarios:'),           module = 'usuarios'    WHERE key LIKE 'users:%';
UPDATE global_action_permissions SET key = REPLACE(key, 'production:', 'produccion:'),     module = 'produccion'  WHERE key LIKE 'production:%';
UPDATE global_action_permissions SET key = REPLACE(key, 'billing:', 'facturacion:'),       module = 'facturacion' WHERE key LIKE 'billing:%';
UPDATE global_action_permissions SET key = REPLACE(key, 'customers:', 'clientes:'),       module = 'clientes'    WHERE key LIKE 'customers:%';
UPDATE global_action_permissions SET key = REPLACE(key, 'finances:', 'finanzas:'),        module = 'finanzas'    WHERE key LIKE 'finances:%';
UPDATE global_action_permissions SET key = REPLACE(key, 'hr:', 'rrhh:'),                  module = 'rrhh'        WHERE key LIKE 'hr:%';
UPDATE global_action_permissions SET key = REPLACE(key, 'reports:', 'reportes:'),         module = 'reportes'    WHERE key LIKE 'reports:%';

UPDATE global_action_permissions SET key = REPLACE(key, 'users.', 'usuarios.'),           module = 'usuarios'    WHERE key LIKE 'users.%';
UPDATE global_action_permissions SET key = REPLACE(key, 'production.', 'produccion.'),     module = 'produccion'  WHERE key LIKE 'production.%';
UPDATE global_action_permissions SET key = REPLACE(key, 'billing.', 'facturacion.'),       module = 'facturacion' WHERE key LIKE 'billing.%';
UPDATE global_action_permissions SET key = REPLACE(key, 'customers.', 'clientes.'),       module = 'clientes'    WHERE key LIKE 'customers.%';
UPDATE global_action_permissions SET key = REPLACE(key, 'finances.', 'finanzas.'),        module = 'finanzas'    WHERE key LIKE 'finances.%';
UPDATE global_action_permissions SET key = REPLACE(key, 'hr.', 'rrhh.'),                  module = 'rrhh'        WHERE key LIKE 'hr.%';
UPDATE global_action_permissions SET key = REPLACE(key, 'reports.', 'reportes.'),         module = 'reportes'    WHERE key LIKE 'reports.%';

UPDATE company_roles
SET permissions = (
  SELECT jsonb_object_agg(
    CASE key
      WHEN 'users'       THEN 'usuarios'
      WHEN 'production'  THEN 'produccion'
      WHEN 'billing'     THEN 'facturacion'
      WHEN 'customers'   THEN 'clientes'
      WHEN 'finances'    THEN 'finanzas'
      WHEN 'hr'          THEN 'rrhh'
      WHEN 'reports'     THEN 'reportes'
      ELSE key
    END,
    value
  )
  FROM jsonb_each(permissions)
)
WHERE permissions IS NOT NULL
  AND permissions::text ~ '"(users|production|billing|customers|finances|hr|reports)"';
