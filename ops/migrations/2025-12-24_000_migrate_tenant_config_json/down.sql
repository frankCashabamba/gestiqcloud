-- Reverse: restore config_json on tenants from company_settings.settings.template_config
-- and remove the rows inserted into company_settings.

UPDATE tenants t
SET config_json = (cs.settings -> 'template_config')
FROM company_settings cs
WHERE cs.tenant_id = t.id
  AND cs.settings ? 'template_config';

UPDATE company_settings
SET settings = settings - 'template_config'
WHERE settings ? 'template_config';
