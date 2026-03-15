-- This was a corrective/idempotent re-run of 2026-03-08_001.
-- Only drop the column if the original migration is also being rolled back.
-- Kept as a no-op to avoid double-dropping overhead_pct.
-- To fully remove overhead_pct, rollback 2026-03-08_001 instead.
SELECT 1;
