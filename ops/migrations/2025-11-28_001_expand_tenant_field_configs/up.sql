-- =============================================================================
-- Migration: 2025-11-28_001_expand_tenant_field_configs
-- Description: Expand tenant_field_configs with aliases, validation, transforms
-- =============================================================================
-- This migration adds new columns to support dynamic field configuration:
--   - aliases: Alternative field names for import detection
--   - field_type: Data type information
--   - validation_pattern: Regex validation
--   - validation_rules: Complex validation rules (JSON)
--   - transform_expression: Value transformation code

BEGIN;

-- Add new columns to tenant_field_configs
-- All are NULLABLE for backward compatibility

ALTER TABLE tenant_field_configs
  ADD COLUMN IF NOT EXISTS aliases JSONB DEFAULT NULL;

ALTER TABLE tenant_field_configs
  ADD COLUMN IF NOT EXISTS field_type VARCHAR(20) DEFAULT NULL;

ALTER TABLE tenant_field_configs
  ADD COLUMN IF NOT EXISTS validation_pattern VARCHAR(500) DEFAULT NULL;

ALTER TABLE tenant_field_configs
  ADD COLUMN IF NOT EXISTS validation_rules JSONB DEFAULT NULL;

ALTER TABLE tenant_field_configs
  ADD COLUMN IF NOT EXISTS transform_expression TEXT DEFAULT NULL;

-- Add constraints to validate data
ALTER TABLE tenant_field_configs
  ADD CONSTRAINT check_aliases_array CHECK (aliases IS NULL OR jsonb_typeof(aliases) = 'array');

ALTER TABLE tenant_field_configs
  ADD CONSTRAINT check_field_type CHECK (
    field_type IS NULL OR field_type IN (
      'string', 'number', 'integer', 'decimal', 'date', 'datetime',
      'time', 'boolean', 'email', 'phone', 'currency', 'percentage',
      'uuid', 'json', 'enum'
    )
  );

ALTER TABLE tenant_field_configs
  ADD CONSTRAINT check_validation_rules_object CHECK (validation_rules IS NULL OR jsonb_typeof(validation_rules) = 'object');

-- Create index for common queries
CREATE INDEX IF NOT EXISTS idx_tenant_field_configs_tenant_module
  ON tenant_field_configs(tenant_id, module);

-- Add comments to columns
COMMENT ON COLUMN tenant_field_configs.aliases IS
  'JSONB array of alternative names for field detection in imports. Example: ["precio", "pvp", "price"]';

COMMENT ON COLUMN tenant_field_configs.field_type IS
  'Data type classification for proper parsing and validation. Values: string, number, date, boolean, email, phone, currency, etc.';

COMMENT ON COLUMN tenant_field_configs.validation_pattern IS
  'Regex pattern as string for field validation. Example: "^[0-9]{1,10}(\\.[0-9]{1,2})?$"';

COMMENT ON COLUMN tenant_field_configs.validation_rules IS
  'Complex validation rules in JSON format. Example: {"min": 0, "max": 999999, "decimal_places": 2}';

COMMENT ON COLUMN tenant_field_configs.transform_expression IS
  'JavaScript code as string to transform/parse field values. Example: "parseFloat(String(v).replace(/[^\d.-]/g, \"\"))"';

COMMIT;
