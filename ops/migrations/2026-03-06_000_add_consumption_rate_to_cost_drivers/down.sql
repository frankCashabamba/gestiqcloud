-- Revert: remove consumption_rate from production_cost_drivers
ALTER TABLE production_cost_drivers
    DROP COLUMN IF EXISTS consumption_rate;
