-- Rollback: imp_documento_status_fields
DROP INDEX IF EXISTS idx_imp_documento_extraction_status;

ALTER TABLE imp_documento
    DROP COLUMN IF EXISTS extraction_status,
    DROP COLUMN IF EXISTS reprocess_status;
