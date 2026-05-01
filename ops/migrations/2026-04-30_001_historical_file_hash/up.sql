-- Migration: 2026-04-30_001_historical_file_hash
-- Add file_hash (SHA-256) column to hist_imports for strong deduplication.
BEGIN;

ALTER TABLE hist_imports ADD COLUMN IF NOT EXISTS file_hash VARCHAR(64);

CREATE INDEX IF NOT EXISTS idx_hist_imports_file_hash
    ON hist_imports(tenant_id, file_hash);

COMMIT;
