-- Migration: 2026-01-06_000_add_import_column_mapping_transforms
-- Description: Add transforms/defaults to import_column_mappings for flexible mapping rules.

BEGIN;

ALTER TABLE public.import_column_mappings
    ADD COLUMN IF NOT EXISTS transforms JSONB,
    ADD COLUMN IF NOT EXISTS defaults JSONB;

COMMIT;
