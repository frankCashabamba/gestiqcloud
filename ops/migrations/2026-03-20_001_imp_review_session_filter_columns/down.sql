BEGIN;

ALTER TABLE IF EXISTS imp_review_session
    DROP COLUMN IF EXISTS filter_columns;

COMMIT;
