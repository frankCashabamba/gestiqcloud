-- Down migration (best-effort). Drops columns if exist.
ALTER TABLE import_attachments DROP COLUMN IF EXISTS page_no;
ALTER TABLE import_batches DROP COLUMN IF EXISTS file_sha256;
ALTER TABLE import_batches DROP COLUMN IF EXISTS parser_choice_confidence;
