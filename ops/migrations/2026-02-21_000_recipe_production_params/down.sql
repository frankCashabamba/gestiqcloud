BEGIN;

ALTER TABLE recipes
    DROP COLUMN IF EXISTS baking_time_minutes,
    DROP COLUMN IF EXISTS oven_temp_celsius,
    DROP COLUMN IF EXISTS rest_time_minutes,
    DROP COLUMN IF EXISTS waste_pct;

COMMIT;
