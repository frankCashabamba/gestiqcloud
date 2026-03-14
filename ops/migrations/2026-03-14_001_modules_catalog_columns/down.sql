-- =============================================================================
-- Rollback: 2026-03-14_001_modules_catalog_columns
-- =============================================================================
BEGIN;

DROP INDEX IF EXISTS modules_url_unique;

ALTER TABLE modules DROP COLUMN IF EXISTS sectors;
ALTER TABLE modules DROP COLUMN IF EXISTS countries;
ALTER TABLE modules DROP COLUMN IF EXISTS aliases;
ALTER TABLE modules DROP COLUMN IF EXISTS dependencies;
ALTER TABLE modules DROP COLUMN IF EXISTS default_enabled;
ALTER TABLE modules DROP COLUMN IF EXISTS required;
ALTER TABLE modules DROP COLUMN IF EXISTS implemented;

COMMIT;
