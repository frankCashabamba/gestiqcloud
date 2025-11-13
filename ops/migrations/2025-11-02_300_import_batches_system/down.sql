-- Rollback: Remove import_batches system

DROP TABLE IF EXISTS import_lineage CASCADE;
DROP TABLE IF EXISTS import_item_corrections CASCADE;
DROP TABLE IF EXISTS import_ocr_jobs CASCADE;
DROP TABLE IF EXISTS import_mappings CASCADE;
DROP TABLE IF EXISTS import_items CASCADE;
DROP TABLE IF EXISTS import_batches CASCADE;
