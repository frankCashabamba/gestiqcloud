-- Add columns that exist in the Product ORM model but were missing a formal migration.
BEGIN;

ALTER TABLE products
    ADD COLUMN IF NOT EXISTS import_aliases  JSON,
    ADD COLUMN IF NOT EXISTS is_raw_material BOOLEAN NOT NULL DEFAULT FALSE;

COMMIT;
