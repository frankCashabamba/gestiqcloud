-- Add consumption_rate to production_cost_drivers
-- Used for automatic energy cost calculation (diesel L/hr, electricity kWh/hr)
ALTER TABLE production_cost_drivers
    ADD COLUMN IF NOT EXISTS consumption_rate NUMERIC(10, 4) NULL;

COMMENT ON COLUMN production_cost_drivers.consumption_rate IS
    'Auto-calc consumption rate per hour (e.g. 2.0 L/hr for diesel, 10.0 kWh/hr for electricity). NULL = manual entry.';
