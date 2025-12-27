-- Migration: 2026-01-06_001_add_import_batches_original_filename
-- Description: Add original_filename to import_batches for better mapping auto-pick.

BEGIN;

ALTER TABLE public.import_batches
    ADD COLUMN IF NOT EXISTS original_filename VARCHAR;

COMMIT;
