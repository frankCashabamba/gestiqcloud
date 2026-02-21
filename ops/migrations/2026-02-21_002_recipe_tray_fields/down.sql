BEGIN;

ALTER TABLE recipes
    DROP COLUMN IF EXISTS trays_per_batch,
    DROP COLUMN IF EXISTS units_per_tray;

COMMIT;
