-- Rollback: 2026-02-14_001_posting_registry

BEGIN;

DROP TABLE IF EXISTS posting_registry;
DROP TABLE IF EXISTS import_resolutions;

COMMIT;
