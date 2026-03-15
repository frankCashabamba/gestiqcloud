BEGIN;

DROP INDEX IF EXISTS ix_country_tax_codes_code;
DROP INDEX IF EXISTS ix_country_tax_codes_country_code;
DROP TABLE IF EXISTS country_tax_codes;

DROP INDEX IF EXISTS ix_country_id_types_code;
DROP INDEX IF EXISTS ix_country_id_types_country_code;
DROP TABLE IF EXISTS country_id_types;

COMMIT;
