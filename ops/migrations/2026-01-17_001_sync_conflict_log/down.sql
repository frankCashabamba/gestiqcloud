-- Migration: 2026-01-17_001_sync_conflict_log (rollback)
-- Description: Drop sync_conflict_log table.

BEGIN;

DROP INDEX IF EXISTS public.idx_sync_conflicts_resolved_at;
DROP INDEX IF EXISTS public.idx_sync_conflicts_entity;
DROP INDEX IF EXISTS public.idx_sync_conflicts_tenant;
DROP TABLE IF EXISTS public.sync_conflict_log;

COMMIT;
