-- Migration: 2026-02-22_000_recipe_costing_columns
-- Description: Add touch/oven/process time columns for advanced costing.

BEGIN;

ALTER TABLE recipes
    ADD COLUMN IF NOT EXISTS touch_minutes_standard INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS oven_minutes_standard INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS process_minutes INTEGER;

COMMENT ON COLUMN recipes.touch_minutes_standard IS 'Minutes of active work (weighing, kneading, shaping, loading, unloading, packaging)';
COMMENT ON COLUMN recipes.oven_minutes_standard IS 'Baking minutes (consumes OVEN resource for diesel/energy)';
COMMENT ON COLUMN recipes.process_minutes IS 'Minutes of passive process time (fermentation/resting), used for planning only';

COMMIT;
