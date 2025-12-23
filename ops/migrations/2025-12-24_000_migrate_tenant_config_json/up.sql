-- Move legacy tenants.config_json into company_settings.settings.template_config
-- and clear the tenant cache to keep settings centralized.

INSERT INTO company_settings (
  tenant_id,
  settings,
  default_language,
  timezone,
  currency,
  primary_color,
  secondary_color,
  allow_custom_roles,
  user_limit,
  operation_type,
  created_at,
  updated_at
)
SELECT
  t.id,
  '{}'::jsonb,
  'es',
  'Europe/Madrid',
  'EUR',
  COALESCE(t.primary_color, '#4f46e5'),
  '#6c757d',
  TRUE,
  10,
  'sales',
  NOW(),
  NOW()
FROM tenants t
LEFT JOIN company_settings cs ON cs.tenant_id = t.id
WHERE cs.tenant_id IS NULL;

UPDATE company_settings cs
SET settings = COALESCE(cs.settings, '{}'::jsonb)
  || jsonb_build_object('template_config', t.config_json)
FROM tenants t
WHERE cs.tenant_id = t.id
  AND t.config_json IS NOT NULL;

UPDATE tenants
SET config_json = NULL
WHERE config_json IS NOT NULL;
