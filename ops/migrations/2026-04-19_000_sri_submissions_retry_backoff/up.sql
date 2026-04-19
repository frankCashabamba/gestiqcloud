BEGIN;

-- Add retry tracking columns to sri_submissions for exponential backoff support.
-- retry_count: number of failed attempts so far (used to compute delay).
-- next_retry_at: earliest timestamp at which this submission may be retried.
--   NULL means "eligible immediately" (new rows or rows reset after success).

ALTER TABLE public.sri_submissions
    ADD COLUMN IF NOT EXISTS retry_count   INTEGER     NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS next_retry_at TIMESTAMPTZ NULL;

-- Index so the retry worker can cheaply fetch eligible ERROR rows.
CREATE INDEX IF NOT EXISTS ix_sri_submissions_retry
    ON public.sri_submissions (tenant_id, status, next_retry_at)
    WHERE status = 'ERROR';

COMMIT;
