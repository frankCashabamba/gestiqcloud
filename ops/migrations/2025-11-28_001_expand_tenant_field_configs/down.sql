-- =============================================================================
-- Rollback: 2025-11-28_001_expand_tenant_field_configs
-- Description: Remove dynamically added columns from tenant_field_configs
-- =============================================================================
-- ⚠️ WARNING: This migration removes columns added for dynamic configuration.
--    Only use if you need to rollback to the previous schema.

BEGIN;

-- Drop the index first
DROP INDEX IF EXISTS idx_tenant_field_configs_tenant_module;

-- Remove columns in reverse order of creation
ALTER TABLE tenant_field_configs
  DROP COLUMN IF EXISTS transform_expression CASCADE,
  DROP COLUMN IF EXISTS validation_rules CASCADE,
  DROP COLUMN IF EXISTS validation_pattern CASCADE,
  DROP COLUMN IF EXISTS field_type CASCADE,
  DROP COLUMN IF EXISTS aliases CASCADE;

COMMIT;
