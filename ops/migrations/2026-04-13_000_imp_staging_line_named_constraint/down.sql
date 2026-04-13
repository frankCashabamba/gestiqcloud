-- Revierte el UNIQUE CONSTRAINT nombrado al índice de expresión original.

ALTER TABLE imp_staging_line
    DROP CONSTRAINT IF EXISTS uq_imp_staging_line_doc_line_sheet;

CREATE UNIQUE INDEX IF NOT EXISTS uq_imp_staging_line_doc_line_sheet
    ON imp_staging_line (documento_id, line_number, COALESCE(sheet_name, '__document__'));
