-- Rollback: 2026-02-22_000_recipe_costing_columns

BEGIN;

ALTER TABLE recipes
    DROP COLUMN IF EXISTS touch_minutes_standard,
    DROP COLUMN IF EXISTS oven_minutes_standard,
    DROP COLUMN IF EXISTS process_minutes;

COMMIT;
