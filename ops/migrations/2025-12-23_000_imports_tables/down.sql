BEGIN;

DROP INDEX IF EXISTS ix_import_ocr_jobs_tenant_status_created;
DROP INDEX IF EXISTS ix_import_ocr_jobs_status_created;
DROP INDEX IF EXISTS ix_import_ocr_jobs_tenant_id;
DROP INDEX IF EXISTS ix_import_lineage_tenant_id;
DROP INDEX IF EXISTS ix_import_lineage_item_id;
DROP INDEX IF EXISTS ix_import_item_corrections_tenant_id;
DROP INDEX IF EXISTS ix_import_item_corrections_item_id;
DROP INDEX IF EXISTS ix_import_mappings_mappings_gin;
DROP INDEX IF EXISTS ix_import_mappings_tenant_source;
DROP INDEX IF EXISTS ix_import_mappings_tenant_id;
DROP INDEX IF EXISTS ix_import_attachments_tenant_id;
DROP INDEX IF EXISTS ix_import_attachments_item_id;
DROP INDEX IF EXISTS ix_import_items_doc_type;
DROP INDEX IF EXISTS ix_import_items_raw_gin;
DROP INDEX IF EXISTS ix_import_items_normalized_gin;
DROP INDEX IF EXISTS ix_import_items_tenant_dedupe;
DROP INDEX IF EXISTS ix_import_items_idempotency_key;
DROP INDEX IF EXISTS ix_import_items_batch_id;
DROP INDEX IF EXISTS ix_import_items_tenant_id;

DROP TABLE IF EXISTS import_ocr_jobs;
DROP TABLE IF EXISTS import_lineage;
DROP TABLE IF EXISTS import_item_corrections;
DROP TABLE IF EXISTS import_mappings;
DROP TABLE IF EXISTS import_attachments;
DROP TABLE IF EXISTS import_items;

COMMIT;
