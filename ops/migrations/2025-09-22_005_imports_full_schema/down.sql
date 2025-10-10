-- Drop in reverse order (safe if tables exist)
DROP INDEX IF EXISTS ix_import_lineage_item;
DROP INDEX IF EXISTS ix_import_items_promoted_hash;
DROP INDEX IF EXISTS ux_import_items_batch_id_idem;
DROP INDEX IF EXISTS ix_import_items_batch_idx;
DROP INDEX IF EXISTS ix_import_batches_empresa_created;

DROP TABLE IF EXISTS import_item_corrections;
DROP TABLE IF EXISTS import_lineage;
DROP TABLE IF EXISTS import_mappings;
DROP TABLE IF EXISTS import_items;
DROP TABLE IF EXISTS import_batches;

