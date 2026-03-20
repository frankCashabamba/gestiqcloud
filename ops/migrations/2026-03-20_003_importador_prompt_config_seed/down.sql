BEGIN;

DELETE FROM sector_field_defaults
WHERE sector = '_system'
  AND module = 'importador.prompt_config';

COMMIT;
