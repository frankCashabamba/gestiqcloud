BEGIN;

ALTER TABLE products
    DROP COLUMN IF EXISTS import_aliases,
    DROP COLUMN IF EXISTS is_raw_material;

COMMIT;
