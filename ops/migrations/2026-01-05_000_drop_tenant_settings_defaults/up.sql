ALTER TABLE tenants ALTER COLUMN base_currency DROP DEFAULT;
ALTER TABLE tenants ALTER COLUMN base_currency DROP NOT NULL;
ALTER TABLE tenants ALTER COLUMN country_code DROP DEFAULT;
ALTER TABLE tenants ALTER COLUMN country_code DROP NOT NULL;
ALTER TABLE tenants ALTER COLUMN primary_color DROP DEFAULT;
ALTER TABLE tenants ALTER COLUMN primary_color DROP NOT NULL;
ALTER TABLE tenants ALTER COLUMN default_template DROP DEFAULT;
ALTER TABLE tenants ALTER COLUMN default_template DROP NOT NULL;

ALTER TABLE company_settings ALTER COLUMN default_language DROP DEFAULT;
ALTER TABLE company_settings ALTER COLUMN default_language DROP NOT NULL;
ALTER TABLE company_settings ALTER COLUMN timezone DROP DEFAULT;
ALTER TABLE company_settings ALTER COLUMN timezone DROP NOT NULL;
ALTER TABLE company_settings ALTER COLUMN currency DROP DEFAULT;
ALTER TABLE company_settings ALTER COLUMN currency DROP NOT NULL;
ALTER TABLE company_settings ALTER COLUMN primary_color DROP DEFAULT;
ALTER TABLE company_settings ALTER COLUMN primary_color DROP NOT NULL;
ALTER TABLE company_settings ALTER COLUMN secondary_color DROP DEFAULT;
ALTER TABLE company_settings ALTER COLUMN secondary_color DROP NOT NULL;
