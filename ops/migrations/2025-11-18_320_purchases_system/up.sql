-- ============================================================================
-- Migration: 2025-11-18_320_purchases_system
-- Description: Purchase orders and purchase line items
-- ============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create ENUM types
DO $$ BEGIN
  CREATE TYPE purchase_status AS ENUM ('DRAFT', 'CONFIRMED', 'RECEIVED', 'INVOICED', 'CANCELLED');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ============================================================================
-- Table: purchases
-- ============================================================================

CREATE TABLE IF NOT EXISTS purchases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Reference
    number VARCHAR(50) NOT NULL UNIQUE,

    -- Supplier
    supplier_id UUID NOT NULL REFERENCES suppliers(id) ON DELETE RESTRICT,

    -- Dates
    order_date DATE NOT NULL,
    expected_delivery_date DATE,
    actual_delivery_date DATE,

    -- Amounts
    subtotal NUMERIC(12, 2) NOT NULL DEFAULT 0,
    tax NUMERIC(12, 2) NOT NULL DEFAULT 0,
    total NUMERIC(12, 2) NOT NULL DEFAULT 0,

    -- Status
    status purchase_status NOT NULL DEFAULT 'DRAFT',

    -- Notes
    notes TEXT,

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_purchases_tenant ON purchases(tenant_id);
CREATE INDEX IF NOT EXISTS idx_purchases_number ON purchases(number);
CREATE INDEX IF NOT EXISTS idx_purchases_supplier ON purchases(supplier_id);
CREATE INDEX IF NOT EXISTS idx_purchases_status ON purchases(status);
CREATE INDEX IF NOT EXISTS idx_purchases_date ON purchases(order_date);

COMMENT ON TABLE purchases IS 'Purchase orders from suppliers';

ALTER TABLE purchases ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_purchases ON purchases;
CREATE POLICY tenant_isolation_purchases ON purchases
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

-- ============================================================================
-- Table: purchase_lines
-- ============================================================================

CREATE TABLE IF NOT EXISTS purchase_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    purchase_id UUID NOT NULL REFERENCES purchases(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE SET NULL,

    -- Item details
    description VARCHAR(255) NOT NULL,
    quantity NUMERIC(14, 3) NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL,
    tax_rate NUMERIC(6, 4) NOT NULL DEFAULT 0.21,
    discount_percent NUMERIC(5, 2) DEFAULT 0,

    -- Calculated
    line_total NUMERIC(12, 2) NOT NULL,

    -- Received
    received_qty NUMERIC(14, 3) DEFAULT 0,

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_purchase_lines_purchase ON purchase_lines(purchase_id);
CREATE INDEX IF NOT EXISTS idx_purchase_lines_product ON purchase_lines(product_id);

COMMENT ON TABLE purchase_lines IS 'Line items of purchase orders';
COMMENT ON COLUMN purchase_lines.received_qty IS 'Quantity received so far';

-- ============================================================================
-- Triggers
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'purchases_updated_at'
    ) THEN
        CREATE TRIGGER purchases_updated_at
            BEFORE UPDATE ON purchases
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END;
$$;

COMMIT;
