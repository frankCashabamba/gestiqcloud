-- Assign default modules to all tenants
-- This ensures all tenants have access to basic modules

INSERT INTO modulos_empresamodulo (empresa_id, modulo_id, tenant_id, activo, fecha_activacion)
SELECT
  t.empresa_id,
  m.id as modulo_id,
  t.id as tenant_id,
  true as activo,
  NOW() as fecha_activacion
FROM tenants t
CROSS JOIN modulos_modulo m
WHERE m.activo = true
ON CONFLICT (empresa_id, modulo_id) DO NOTHING;

-- Assign modules to all tenant users (ModuloAsignado)
-- Disable trigger temporarily to avoid tenant_id GUC requirement
ALTER TABLE modulos_moduloasignado DISABLE TRIGGER ALL;

INSERT INTO modulos_moduloasignado (empresa_id, usuario_id, modulo_id, tenant_id, fecha_asignacion, ver_modulo_auto)
SELECT DISTINCT
  tua.empresa_id,
  tua.id as usuario_id,
  m.id as modulo_id,
  tua.tenant_id,
  NOW() as fecha_asignacion,
  true as ver_modulo_auto
FROM usuarios_usuarioempresa tua
CROSS JOIN modulos_modulo m
WHERE m.activo = true
  AND tua.tenant_id IS NOT NULL
ON CONFLICT (usuario_id, modulo_id, empresa_id) DO NOTHING;

ALTER TABLE modulos_moduloasignado ENABLE TRIGGER ALL;
