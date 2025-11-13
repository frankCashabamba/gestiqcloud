-- Imports indexes and query plans sanity
-- Safe to run on empty DB; uses EXPLAIN only (no ANALYZE to avoid side effects)

SET client_min_messages = warning;
SET statement_timeout = '30s';
-- Hint to prefer index paths when plausible
SET enable_seqscan = off;

-- 1) Dedupe promoted: should use ix_import_items_promoted_hash
EXPLAIN
SELECT 1
FROM import_items ii
JOIN import_batches ib ON ii.batch_id = ib.id
WHERE ib.tenant_id = 0
  AND ii.dedupe_hash = '0000000000000000000000000000000000000000000000000000000000000000'
  AND ii.status = 'PROMOTED'
LIMIT 1;

-- 2) Items by batch ordered: should use ix_import_items_batch_idx
EXPLAIN
SELECT ii.id, ii.idx, ii.status
FROM import_items ii
JOIN import_batches ib ON ii.batch_id = ib.id
WHERE ib.tenant_id = 0
  AND ib.id = '00000000-0000-0000-0000-000000000000'::uuid
ORDER BY ii.idx ASC;

-- 3) Batches by empresa recency: should use ix_import_batches_empresa_created
EXPLAIN
SELECT id, source_type, origin, status, created_at
FROM import_batches
WHERE tenant_id = 0
ORDER BY created_at DESC
LIMIT 20;

-- 4) Idempotency unique constraint exists (metadata check)
SELECT indexname, indexdef
FROM pg_indexes
WHERE indexname = 'ux_import_items_batch_id_idem';

