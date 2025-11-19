-- Migration: 2025-11-19_903_add_parser_fields
-- Description: Add parser_id and related fields to import_batches

BEGIN;

-- Add parser fields to import_batches
ALTER TABLE import_batches
    ADD COLUMN IF NOT EXISTS parser_id VARCHAR(100),
    ADD COLUMN IF NOT EXISTS parser_choice_confidence NUMERIC,
    ADD COLUMN IF NOT EXISTS suggested_parser VARCHAR(100),
    ADD COLUMN IF NOT EXISTS classification_confidence NUMERIC,
    ADD COLUMN IF NOT EXISTS ai_enhanced BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS ai_provider VARCHAR(50);

-- Add updated_at for audit
ALTER TABLE import_batches
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

COMMIT;
