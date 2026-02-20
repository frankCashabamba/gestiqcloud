-- Migration: Stock Transfers table
-- Date: 2026-02-16
-- Purpose: Enable warehouse-to-warehouse stock transfers with status tracking

-- Create stock_transfers table if it doesn't exist
CREATE TABLE IF NOT EXISTS stock_transfers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    from_warehouse_id UUID NOT NULL REFERENCES warehouses(id) ON DELETE RESTRICT,
    to_warehouse_id UUID NOT NULL REFERENCES warehouses(id) ON DELETE RESTRICT,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity NUMERIC(14, 6) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'in_transit', 'completed', 'cancelled')),
    reason VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Indexes for common queries
    CONSTRAINT chk_different_warehouses CHECK (from_warehouse_id != to_warehouse_id),
    CONSTRAINT chk_positive_quantity CHECK (quantity > 0)
);

-- RLS Policy: Users can only access their tenant's transfers
ALTER TABLE stock_transfers ENABLE ROW LEVEL SECURITY;

CREATE POLICY stock_transfers_tenant_isolation ON stock_transfers
    USING (tenant_id = COALESCE(current_setting('app.tenant_id', true)::uuid, tenant_id));

CREATE POLICY stock_transfers_insert ON stock_transfers
    FOR INSERT WITH CHECK (tenant_id = COALESCE(current_setting('app.tenant_id', true)::uuid, tenant_id));

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_stock_transfers_tenant_id ON stock_transfers(tenant_id);
CREATE INDEX IF NOT EXISTS idx_stock_transfers_from_warehouse ON stock_transfers(from_warehouse_id);
CREATE INDEX IF NOT EXISTS idx_stock_transfers_to_warehouse ON stock_transfers(to_warehouse_id);
CREATE INDEX IF NOT EXISTS idx_stock_transfers_product ON stock_transfers(product_id);
CREATE INDEX IF NOT EXISTS idx_stock_transfers_status ON stock_transfers(status);
CREATE INDEX IF NOT EXISTS idx_stock_transfers_created_at ON stock_transfers(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_stock_transfers_tenant_status ON stock_transfers(tenant_id, status);
