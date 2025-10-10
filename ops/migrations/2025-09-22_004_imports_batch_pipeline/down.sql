-- Rollback for Imports pipeline schema (PostgreSQL)

-- Drop dependents in reverse order
DROP TABLE IF EXISTS import_lineage;
DROP TABLE IF EXISTS import_item_corrections;
DROP TABLE IF EXISTS import_mappings;
DROP INDEX IF EXISTS ix_import_items_dedupe;
DROP INDEX IF EXISTS ix_import_items_batch;
DROP INDEX IF EXISTS uq_import_item_idem;
DROP TABLE IF EXISTS import_items;
DROP TABLE IF EXISTS import_batches;

-- Remove linkage columns from auditoria_importacion
ALTER TABLE auditoria_importacion
    DROP COLUMN IF EXISTS item_id,
    DROP COLUMN IF EXISTS batch_id;

