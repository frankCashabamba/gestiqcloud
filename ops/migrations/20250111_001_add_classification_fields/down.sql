-- Rollback: Remove Fase A classification fields
-- Date: 2025-01-11

ALTER TABLE import_batches
DROP COLUMN IF EXISTS suggested_parser,
DROP COLUMN IF EXISTS classification_confidence,
DROP COLUMN IF EXISTS ai_enhanced,
DROP COLUMN IF EXISTS ai_provider;

DROP INDEX IF EXISTS idx_import_batches_ai_provider;
DROP INDEX IF EXISTS idx_import_batches_ai_enhanced;
