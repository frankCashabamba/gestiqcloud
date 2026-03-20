BEGIN;

ALTER TABLE IF EXISTS imp_review_session
    ADD COLUMN IF NOT EXISTS filter_columns JSONB NOT NULL DEFAULT '[]'::jsonb;

COMMIT;
