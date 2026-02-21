-- Migration: 2026-02-21_001_production_cost_drivers
-- Description: Add tables for production cost drivers, recipe cost lines, and production order costs.

BEGIN;

-- 1. Catalog of cost types per tenant (labor, energy, packaging, overhead, etc.)
CREATE TABLE IF NOT EXISTS production_cost_drivers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    code VARCHAR(30) NOT NULL,
    name VARCHAR(100) NOT NULL,
    unit VARCHAR(20) NOT NULL DEFAULT 'hour',
    default_rate NUMERIC(12,4) NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(tenant_id, code)
);

CREATE INDEX IF NOT EXISTS idx_cost_drivers_tenant ON production_cost_drivers(tenant_id);

COMMENT ON TABLE production_cost_drivers IS 'Catalog of indirect cost types: labor roles, energy, packaging, overhead';
COMMENT ON COLUMN production_cost_drivers.code IS 'Unique code per tenant: LABOR_BAKER, ENERGY_OVEN, PACKAGING, etc.';
COMMENT ON COLUMN production_cost_drivers.unit IS 'Unit of measure: hour, kwh, unit, flat';
COMMENT ON COLUMN production_cost_drivers.default_rate IS 'Default cost per unit of the driver';

-- 2. Standard costs expected per recipe (linked to drivers)
CREATE TABLE IF NOT EXISTS recipe_cost_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipe_id UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    driver_id UUID NOT NULL REFERENCES production_cost_drivers(id) ON DELETE RESTRICT,
    qty_standard NUMERIC(12,4) NOT NULL DEFAULT 0,
    headcount INTEGER NOT NULL DEFAULT 1,
    rate_override NUMERIC(12,4),
    notes TEXT,
    line_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_recipe_cost_lines_recipe ON recipe_cost_lines(recipe_id);
CREATE INDEX IF NOT EXISTS idx_recipe_cost_lines_driver ON recipe_cost_lines(driver_id);

COMMENT ON TABLE recipe_cost_lines IS 'Standard indirect costs per recipe (labor, energy, etc.)';
COMMENT ON COLUMN recipe_cost_lines.qty_standard IS 'Standard quantity: hours, kwh, units depending on driver';
COMMENT ON COLUMN recipe_cost_lines.headcount IS 'Number of people (applicable for labor drivers)';
COMMENT ON COLUMN recipe_cost_lines.rate_override IS 'Override rate for this line (NULL = use driver default_rate)';

-- 3. Actual costs per production order/batch (linked to drivers)
CREATE TABLE IF NOT EXISTS production_order_costs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES production_orders(id) ON DELETE CASCADE,
    driver_id UUID NOT NULL REFERENCES production_cost_drivers(id) ON DELETE RESTRICT,
    qty_actual NUMERIC(12,4) NOT NULL DEFAULT 0,
    headcount_actual INTEGER NOT NULL DEFAULT 1,
    rate_applied NUMERIC(12,4) NOT NULL DEFAULT 0,
    cost_total NUMERIC(12,4) GENERATED ALWAYS AS (qty_actual * rate_applied * headcount_actual) STORED,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_prod_order_costs_order ON production_order_costs(order_id);
CREATE INDEX IF NOT EXISTS idx_prod_order_costs_driver ON production_order_costs(driver_id);

COMMENT ON TABLE production_order_costs IS 'Actual indirect costs recorded per production batch';
COMMENT ON COLUMN production_order_costs.cost_total IS 'Auto-calculated: qty_actual * rate_applied * headcount_actual';

COMMIT;
