BEGIN;

DELETE FROM sector_field_defaults
WHERE sector = '_system'
  AND module IN ('importador.file_support', 'importador.doc_type_patterns');

COMMIT;
