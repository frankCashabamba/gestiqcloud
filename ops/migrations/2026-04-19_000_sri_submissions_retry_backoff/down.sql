BEGIN;

DROP INDEX IF EXISTS public.ix_sri_submissions_retry;

ALTER TABLE public.sri_submissions
    DROP COLUMN IF EXISTS next_retry_at,
    DROP COLUMN IF EXISTS retry_count;

COMMIT;
