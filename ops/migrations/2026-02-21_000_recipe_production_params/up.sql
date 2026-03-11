-- Migration: 2026-02-21_000_recipe_production_params
-- Description: Add production parameters to recipes for better yield calculation.

BEGIN;

ALTER TABLE recipes
    ADD COLUMN IF NOT EXISTS baking_time_minutes INTEGER,
    ADD COLUMN IF NOT EXISTS oven_temp_celsius INTEGER,
    ADD COLUMN IF NOT EXISTS rest_time_minutes INTEGER,
    ADD COLUMN IF NOT EXISTS waste_pct NUMERIC(5,2) DEFAULT 0;

COMMENT ON COLUMN recipes.baking_time_minutes IS 'Baking time in minutes';
COMMENT ON COLUMN recipes.oven_temp_celsius IS 'Oven temperature in °C';
COMMENT ON COLUMN recipes.rest_time_minutes IS 'Resting/fermentation time in minutes';
COMMENT ON COLUMN recipes.waste_pct IS 'Porcentaje de merma (0-100)';

COMMIT;
