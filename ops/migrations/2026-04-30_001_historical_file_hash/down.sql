-- Migration: 2026-04-30_001_historical_file_hash (rollback)
BEGIN;

DROP INDEX IF EXISTS idx_hist_imports_file_hash;

ALTER TABLE hist_imports DROP COLUMN IF EXISTS file_hash;

COMMIT;
