-- Add template V2 support columns (no Alembic)
-- Run manually in staging/prod. Compatible with Postgres and SQLite (tests).

-- Import batches: file sha + parser confidence JSON
ALTER TABLE import_batches ADD COLUMN IF NOT EXISTS file_sha256 VARCHAR;
ALTER TABLE import_batches ADD COLUMN IF NOT EXISTS parser_choice_confidence JSONB;

-- Import attachments: page number for OCR page tracking
ALTER TABLE import_attachments ADD COLUMN IF NOT EXISTS page_no INTEGER;

-- Backfill defaults
UPDATE import_batches SET parser_choice_confidence = '{}'::jsonb WHERE parser_choice_confidence IS NULL;
