-- Migration: 2025-11-20_906_fix_schema_issues (down)
-- Revert schema fixes

BEGIN;

-- Drop the unique index
DROP INDEX IF EXISTS idx_import_items_tenant_idempotency;

-- Remove added columns
ALTER TABLE sales DROP COLUMN IF EXISTS taxes;
ALTER TABLE sales DROP COLUMN IF EXISTS estado;

-- Revert languages.code column size
ALTER TABLE languages ALTER COLUMN code TYPE VARCHAR(10);

COMMIT;
