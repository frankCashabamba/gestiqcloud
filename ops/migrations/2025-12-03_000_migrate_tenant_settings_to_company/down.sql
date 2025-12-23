-- Recreate legacy tenant_settings table and copy data back from company_settings (best-effort)
BEGIN;

CREATE TABLE IF NOT EXISTS tenant_settings (
  id SERIAL PRIMARY KEY,
  tenant_id UUID UNIQUE,
  default_language VARCHAR(10),
  timezone VARCHAR(50),
  currency VARCHAR(10),
  company_logo VARCHAR(100),
  secondary_color VARCHAR(7),
  primary_color VARCHAR(7),
  allow_custom_roles BOOLEAN,
  user_limit INTEGER,
  working_days JSON,
  business_hours JSON,
  operation_type VARCHAR,
  company_name VARCHAR,
  tax_id VARCHAR,
  tax_regime VARCHAR,
  settings JSONB,
  pos_config JSONB,
  invoice_config JSONB,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  language_id INTEGER,
  currency_id INTEGER
);

INSERT INTO tenant_settings (
  tenant_id,
  default_language,
  timezone,
  currency,
  company_logo,
  secondary_color,
  primary_color,
  allow_custom_roles,
  user_limit,
  working_days,
  business_hours,
  operation_type,
  company_name,
  tax_id,
  tax_regime,
  settings,
  pos_config,
  invoice_config,
  created_at,
  updated_at,
  language_id,
  currency_id
)
SELECT
  cs.tenant_id,
  cs.default_language,
  cs.timezone,
  cs.currency,
  cs.company_logo,
  cs.secondary_color,
  cs.primary_color,
  cs.allow_custom_roles,
  cs.user_limit,
  cs.working_days,
  cs.business_hours,
  cs.operation_type,
  cs.company_name,
  cs.tax_id,
  cs.tax_regime,
  cs.settings,
  cs.pos_config,
  cs.invoice_config,
  cs.created_at,
  cs.updated_at,
  cs.language_id,
  cs.currency_id
FROM company_settings cs
WHERE NOT EXISTS (
  SELECT 1 FROM tenant_settings ts WHERE ts.tenant_id = cs.tenant_id
);

COMMIT;
