-- Migration: 2026-02-21_002_recipe_tray_fields
-- Description: Add tray configuration per recipe for accurate oven energy calculation.

BEGIN;

ALTER TABLE recipes
    ADD COLUMN IF NOT EXISTS trays_per_batch INTEGER,
    ADD COLUMN IF NOT EXISTS units_per_tray INTEGER;

COMMENT ON COLUMN recipes.trays_per_batch IS 'Number of trays per oven batch';
COMMENT ON COLUMN recipes.units_per_tray IS 'Units produced per tray (varies by product size)';

COMMIT;
