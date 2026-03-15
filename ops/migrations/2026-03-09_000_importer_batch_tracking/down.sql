DROP INDEX IF EXISTS ix_imp_batch_item_hash_sha256;
DROP INDEX IF EXISTS ix_imp_batch_item_tenant_id;
DROP INDEX IF EXISTS ix_imp_batch_item_documento_id;
DROP INDEX IF EXISTS ix_imp_batch_item_batch_id;
DROP TABLE IF EXISTS imp_batch_item;

DROP INDEX IF EXISTS ix_imp_batch_import_estado;
DROP INDEX IF EXISTS ix_imp_batch_import_tenant_id;
DROP TABLE IF EXISTS imp_batch_import;
