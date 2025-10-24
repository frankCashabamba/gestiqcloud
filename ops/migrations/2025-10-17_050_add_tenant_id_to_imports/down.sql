-- Rollback migration: Remove tenant_id from imports module tables
-- WARNING: This will drop tenant_id columns and revert JSONB to JSON

-- Drop indexes
DROP INDEX IF EXISTS ix_import_items_doc_type;
DROP INDEX IF EXISTS ix_import_items_raw_gin;
DROP INDEX IF EXISTS ix_import_items_normalized_gin;
DROP INDEX IF EXISTS ix_import_items_tenant_dedupe;
DROP INDEX IF EXISTS ix_import_items_tenant_id;
DROP INDEX IF EXISTS ix_import_batches_tenant_status_created;
DROP INDEX IF EXISTS ix_import_attachments_tenant_id;
DROP INDEX IF EXISTS ix_import_ocr_jobs_tenant_status_created;
DROP INDEX IF EXISTS ix_import_ocr_jobs_tenant_id;
DROP INDEX IF EXISTS ix_import_mappings_tenant_source;
DROP INDEX IF EXISTS ix_import_mappings_mappings_gin;
DROP INDEX IF EXISTS uq_import_items_tenant_idem;

-- Restore old unique constraint
CREATE UNIQUE INDEX IF NOT EXISTS uq_import_item_idem ON public.import_items (idempotency_key);

-- Revert JSONB to JSON
ALTER TABLE public.import_items
  ALTER COLUMN raw TYPE json USING raw::json,
  ALTER COLUMN normalized TYPE json USING normalized::json,
  ALTER COLUMN errors TYPE json USING errors::json;

ALTER TABLE public.import_mappings
  ALTER COLUMN mappings TYPE json USING mappings::json,
  ALTER COLUMN transforms TYPE json USING transforms::json,
  ALTER COLUMN defaults TYPE json USING defaults::json,
  ALTER COLUMN dedupe_keys TYPE json USING dedupe_keys::json;

ALTER TABLE public.import_ocr_jobs
  ALTER COLUMN result TYPE json USING result::json;

-- Drop foreign keys and tenant_id columns
ALTER TABLE public.import_items DROP CONSTRAINT IF EXISTS fk_import_items_tenant;
ALTER TABLE public.import_items DROP COLUMN IF EXISTS tenant_id;

ALTER TABLE public.import_attachments DROP CONSTRAINT IF EXISTS fk_import_attachments_tenant;
ALTER TABLE public.import_attachments DROP COLUMN IF EXISTS tenant_id;

ALTER TABLE public.import_ocr_jobs DROP CONSTRAINT IF EXISTS fk_import_ocr_jobs_tenant;
ALTER TABLE public.import_ocr_jobs DROP COLUMN IF EXISTS tenant_id;
