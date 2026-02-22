-- Migration: 2026-02-22_000_recipe_costing_columns
-- Description: Add touch/oven/process time columns for advanced costing.

BEGIN;

ALTER TABLE recipes
    ADD COLUMN IF NOT EXISTS touch_minutes_standard INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS oven_minutes_standard INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS process_minutes INTEGER;

COMMENT ON COLUMN recipes.touch_minutes_standard IS 'Minutos de trabajo activo (pesar, amasar, bolear, cargar, descargar, empaque)';
COMMENT ON COLUMN recipes.oven_minutes_standard IS 'Minutos de horneado (consume recurso HORNO para diésel/energía)';
COMMENT ON COLUMN recipes.process_minutes IS 'Minutos de proceso pasivo (fermentación/reposo): solo para planificación';

COMMIT;
