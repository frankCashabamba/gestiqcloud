UPDATE tenants SET base_currency = 'EUR' WHERE base_currency IS NULL;
UPDATE tenants SET country_code = 'ES' WHERE country_code IS NULL;
UPDATE tenants SET primary_color = '#4f46e5' WHERE primary_color IS NULL;
UPDATE tenants SET default_template = 'client' WHERE default_template IS NULL;

ALTER TABLE tenants ALTER COLUMN base_currency SET DEFAULT 'EUR';
ALTER TABLE tenants ALTER COLUMN base_currency SET NOT NULL;
ALTER TABLE tenants ALTER COLUMN country_code SET DEFAULT 'ES';
ALTER TABLE tenants ALTER COLUMN country_code SET NOT NULL;
ALTER TABLE tenants ALTER COLUMN primary_color SET DEFAULT '#4f46e5';
ALTER TABLE tenants ALTER COLUMN primary_color SET NOT NULL;
ALTER TABLE tenants ALTER COLUMN default_template SET DEFAULT 'client';
ALTER TABLE tenants ALTER COLUMN default_template SET NOT NULL;

UPDATE company_settings SET default_language = 'es' WHERE default_language IS NULL;
UPDATE company_settings SET timezone = 'UTC' WHERE timezone IS NULL;
UPDATE company_settings SET currency = 'EUR' WHERE currency IS NULL;
UPDATE company_settings SET primary_color = '#4f46e5' WHERE primary_color IS NULL;
UPDATE company_settings SET secondary_color = '#6c757d' WHERE secondary_color IS NULL;

ALTER TABLE company_settings ALTER COLUMN default_language SET DEFAULT 'es';
ALTER TABLE company_settings ALTER COLUMN default_language SET NOT NULL;
ALTER TABLE company_settings ALTER COLUMN timezone SET DEFAULT 'UTC';
ALTER TABLE company_settings ALTER COLUMN timezone SET NOT NULL;
ALTER TABLE company_settings ALTER COLUMN currency SET DEFAULT 'EUR';
ALTER TABLE company_settings ALTER COLUMN currency SET NOT NULL;
ALTER TABLE company_settings ALTER COLUMN primary_color SET DEFAULT '#4f46e5';
ALTER TABLE company_settings ALTER COLUMN primary_color SET NOT NULL;
ALTER TABLE company_settings ALTER COLUMN secondary_color SET DEFAULT '#6c757d';
ALTER TABLE company_settings ALTER COLUMN secondary_color SET NOT NULL;
