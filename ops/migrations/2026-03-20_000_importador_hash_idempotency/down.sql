BEGIN;

DROP INDEX IF EXISTS uq_imp_documento_tenant_hash;
CREATE INDEX IF NOT EXISTS idx_imp_doc_hash ON imp_documento(hash_sha256);

DROP INDEX IF EXISTS uq_imp_staging_line_doc_line_sheet;
ALTER TABLE imp_staging_line
    ADD CONSTRAINT imp_staging_line_documento_id_line_number_sheet_name_key
    UNIQUE (documento_id, line_number, sheet_name);

COMMIT;
