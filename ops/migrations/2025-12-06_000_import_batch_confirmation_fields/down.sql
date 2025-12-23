-- Rollback: Remove confirmation fields from import_batches table
-- Date: 2025-12-06
-- WARNING: This will drop columns and lose data

-- Drop index first
DROP INDEX IF EXISTS idx_import_batches_requires_confirmation;

-- Drop columns
ALTER TABLE import_batches DROP COLUMN IF EXISTS requires_confirmation;
ALTER TABLE import_batches DROP COLUMN IF EXISTS confirmed_at;
ALTER TABLE import_batches DROP COLUMN IF EXISTS confirmed_parser;
ALTER TABLE import_batches DROP COLUMN IF EXISTS user_override;
