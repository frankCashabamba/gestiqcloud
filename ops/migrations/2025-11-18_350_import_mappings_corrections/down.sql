-- Rollback: 2025-11-18_350_import_mappings_corrections

BEGIN;

DROP TRIGGER IF EXISTS import_mappings_updated_at ON import_mappings;

DROP POLICY IF EXISTS tenant_isolation_import_mappings ON import_mappings;

-- Remove columns from import_mappings (only if we added them)
ALTER TABLE import_mappings
DROP COLUMN IF EXISTS is_active,
DROP COLUMN IF EXISTS is_template,
DROP COLUMN IF EXISTS description,
DROP COLUMN IF EXISTS mapping_config,
DROP COLUMN IF EXISTS updated_at;

-- Drop constraints
ALTER TABLE import_mappings DROP CONSTRAINT IF EXISTS import_mappings_tenant_name_unique;

DROP FUNCTION IF EXISTS update_updated_at_column();

COMMIT;
