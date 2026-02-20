-- Rollback: 2026-02-14_000_document_layer

BEGIN;

ALTER TABLE IF EXISTS import_batches DROP COLUMN IF EXISTS stats;
ALTER TABLE IF EXISTS import_batches DROP COLUMN IF EXISTS document_version_id;
DROP TABLE IF EXISTS document_versions;
DROP TABLE IF EXISTS document_files;

COMMIT;
