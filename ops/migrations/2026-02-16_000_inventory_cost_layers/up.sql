CREATE TABLE IF NOT EXISTS inventory_cost_layers (
    id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    warehouse_id UUID NOT NULL,
    product_id UUID NOT NULL,
    remaining_qty NUMERIC(14,6) NOT NULL DEFAULT 0,
    unit_cost NUMERIC(14,6) NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cost_layers_lookup
    ON inventory_cost_layers (tenant_id, warehouse_id, product_id)
    WHERE remaining_qty > 0;
