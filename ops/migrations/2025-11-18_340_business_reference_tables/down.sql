-- Rollback: 2025-11-18_340_business_reference_tables

BEGIN;

DROP TRIGGER IF EXISTS sector_field_defaults_updated_at ON sector_field_defaults;
DROP TRIGGER IF EXISTS sector_templates_updated_at ON sector_templates;
DROP TRIGGER IF EXISTS user_profiles_updated_at ON user_profiles;
DROP TRIGGER IF EXISTS business_hours_updated_at ON business_hours;
DROP TRIGGER IF EXISTS company_categories_updated_at ON company_categories;
DROP TRIGGER IF EXISTS business_categories_updated_at ON business_categories;
DROP TRIGGER IF EXISTS business_types_updated_at ON business_types;

DROP TABLE IF EXISTS sector_field_defaults CASCADE;
DROP TABLE IF EXISTS sector_templates CASCADE;
DROP TABLE IF EXISTS user_profiles CASCADE;
DROP TABLE IF EXISTS business_hours CASCADE;
DROP TABLE IF EXISTS company_categories CASCADE;
DROP TABLE IF EXISTS business_categories CASCADE;
DROP TABLE IF EXISTS business_types CASCADE;

DROP FUNCTION IF EXISTS update_updated_at_column();

COMMIT;
