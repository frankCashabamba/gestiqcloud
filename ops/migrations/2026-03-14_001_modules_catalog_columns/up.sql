-- =============================================================================
-- Migration: 2026-03-14_001_modules_catalog_columns
-- Description: Add professional catalog columns to modules table
-- =============================================================================
-- Adds metadata columns to support the module catalog driven from BD:
--   - implemented: whether the module is actually built
--   - required: whether tenants cannot disable it
--   - default_enabled: whether it is enabled at onboarding
--   - dependencies: JSONB list of module IDs this module requires
--   - aliases: JSONB list of legacy/alternate IDs that resolve to this module
--   - countries: JSONB list of country codes where this module is available
--   - sectors: JSONB list of sector codes (NULL = all sectors)
-- Also creates the unique index on url used for ON CONFLICT upserts.

BEGIN;

ALTER TABLE modules
  ADD COLUMN IF NOT EXISTS implemented     BOOLEAN NOT NULL DEFAULT TRUE;

ALTER TABLE modules
  ADD COLUMN IF NOT EXISTS required        BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE modules
  ADD COLUMN IF NOT EXISTS default_enabled BOOLEAN NOT NULL DEFAULT TRUE;

ALTER TABLE modules
  ADD COLUMN IF NOT EXISTS dependencies    JSONB;

ALTER TABLE modules
  ADD COLUMN IF NOT EXISTS aliases         JSONB;

ALTER TABLE modules
  ADD COLUMN IF NOT EXISTS countries       JSONB;

ALTER TABLE modules
  ADD COLUMN IF NOT EXISTS sectors         JSONB;

-- Unique index on url for idempotent upserts via ON CONFLICT (url)
CREATE UNIQUE INDEX IF NOT EXISTS modules_url_unique
  ON modules (url);

COMMIT;
