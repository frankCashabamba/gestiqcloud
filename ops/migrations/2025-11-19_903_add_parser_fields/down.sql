-- Migration: 2025-11-19_903_add_parser_fields (ROLLBACK)
-- Description: Remove parser_id and related fields from import_batches

BEGIN;

ALTER TABLE import_batches
    DROP COLUMN IF EXISTS parser_id,
    DROP COLUMN IF EXISTS parser_choice_confidence,
    DROP COLUMN IF EXISTS suggested_parser,
    DROP COLUMN IF EXISTS classification_confidence,
    DROP COLUMN IF EXISTS ai_enhanced,
    DROP COLUMN IF EXISTS ai_provider,
    DROP COLUMN IF EXISTS updated_at;

COMMIT;
