-- Migration: 2026-02-24_000_field_config_dynamic_types
-- Description: Add field_type, options, validation_pattern to sector_field_defaults;
--              add options to tenant_field_configs.

BEGIN;

-- Add field_type, options, validation_pattern to sector_field_defaults
ALTER TABLE sector_field_defaults ADD COLUMN IF NOT EXISTS field_type VARCHAR(20) DEFAULT NULL;
ALTER TABLE sector_field_defaults ADD COLUMN IF NOT EXISTS options JSONB DEFAULT NULL;
ALTER TABLE sector_field_defaults ADD COLUMN IF NOT EXISTS validation_pattern VARCHAR(500) DEFAULT NULL;

-- Add options to tenant_field_configs
ALTER TABLE tenant_field_configs ADD COLUMN IF NOT EXISTS options JSONB DEFAULT NULL;

-- Constraints: options must be array (wrapped in DO block for idempotency)
DO $$
BEGIN
    ALTER TABLE sector_field_defaults ADD CONSTRAINT check_sfd_options_array CHECK (options IS NULL OR jsonb_typeof(options) = 'array');
EXCEPTION WHEN duplicate_object THEN NULL;
END$$;

DO $$
BEGIN
    ALTER TABLE tenant_field_configs ADD CONSTRAINT check_tfc_options_array CHECK (options IS NULL OR jsonb_typeof(options) = 'array');
EXCEPTION WHEN duplicate_object THEN NULL;
END$$;

COMMIT;
