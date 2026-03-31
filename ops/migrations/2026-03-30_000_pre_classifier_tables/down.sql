BEGIN;

DROP TABLE IF EXISTS imp_header_doc_type CASCADE;
DROP TABLE IF EXISTS imp_filename_pattern CASCADE;

ALTER TABLE imp_field_alias
    DROP COLUMN IF EXISTS source,
    DROP COLUMN IF EXISTS confirmed_count,
    DROP COLUMN IF EXISTS last_seen_at;

DROP INDEX IF EXISTS imp_field_alias_global_uq;

DELETE FROM sector_field_defaults
WHERE sector = '_system' AND module = 'importador.pre_classifier';

COMMIT;
