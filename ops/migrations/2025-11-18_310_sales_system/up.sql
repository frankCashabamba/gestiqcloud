-- ============================================================================
-- Migration: 2025-11-18_310_sales_system
-- Description: Sales orders, delivery and sales tracking
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
  CREATE TYPE sales_order_status AS ENUM ('DRAFT', 'CONFIRMED', 'SHIPPED', 'DELIVERED', 'CANCELLED');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE delivery_status AS ENUM ('PENDING', 'IN_TRANSIT', 'DELIVERED', 'RETURNED');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ============================================================================
-- Table: sales_orders
-- ============================================================================

CREATE TABLE IF NOT EXISTS sales_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Reference
    number VARCHAR(50) NOT NULL UNIQUE,

    -- Customer
    customer_id UUID REFERENCES clients(id) ON DELETE SET NULL,

    -- Dates
    order_date DATE NOT NULL,
    required_date DATE,

    -- Amounts
    subtotal NUMERIC(12, 2) NOT NULL DEFAULT 0,
    tax NUMERIC(12, 2) NOT NULL DEFAULT 0,
    total NUMERIC(12, 2) NOT NULL DEFAULT 0,
    currency CHAR(3) DEFAULT 'EUR',

    -- Status
    status sales_order_status NOT NULL DEFAULT 'DRAFT',

    -- Notes
    notes TEXT,

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sales_orders_tenant ON sales_orders(tenant_id);
CREATE INDEX IF NOT EXISTS idx_sales_orders_number ON sales_orders(number);
CREATE INDEX IF NOT EXISTS idx_sales_orders_customer ON sales_orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_sales_orders_status ON sales_orders(status);
CREATE INDEX IF NOT EXISTS idx_sales_orders_date ON sales_orders(order_date);

COMMENT ON TABLE sales_orders IS 'Sales orders from customers';

ALTER TABLE sales_orders ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_sales_orders ON sales_orders;
CREATE POLICY tenant_isolation_sales_orders ON sales_orders
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

-- ============================================================================
-- Table: sales_order_items
-- ============================================================================

CREATE TABLE IF NOT EXISTS sales_order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sales_order_id UUID NOT NULL REFERENCES sales_orders(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE SET NULL,

    -- Item details
    quantity NUMERIC(14, 3) NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL,
    tax_rate NUMERIC(6, 4) NOT NULL DEFAULT 0.21,
    discount_percent NUMERIC(5, 2) DEFAULT 0,

    -- Calculated
    line_total NUMERIC(12, 2) NOT NULL,

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sales_order_items_order ON sales_order_items(sales_order_id);
CREATE INDEX IF NOT EXISTS idx_sales_order_items_product ON sales_order_items(product_id);

COMMENT ON TABLE sales_order_items IS 'Line items of sales orders';

-- ============================================================================
-- Table: sales
-- ============================================================================

CREATE TABLE IF NOT EXISTS sales (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Reference
    number VARCHAR(50) NOT NULL UNIQUE,
    sales_order_id UUID REFERENCES sales_orders(id) ON DELETE SET NULL,

    -- Customer
    customer_id UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,

    -- Amounts
    subtotal NUMERIC(12, 2) NOT NULL DEFAULT 0,
    tax NUMERIC(12, 2) NOT NULL DEFAULT 0,
    total NUMERIC(12, 2) NOT NULL DEFAULT 0,

    -- Date
    sale_date DATE NOT NULL,

    -- Notes
    notes TEXT,

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sales_tenant ON sales(tenant_id);
CREATE INDEX IF NOT EXISTS idx_sales_number ON sales(number);
CREATE INDEX IF NOT EXISTS idx_sales_customer ON sales(customer_id);
CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(sale_date);

COMMENT ON TABLE sales IS 'Finalized sales transactions';

ALTER TABLE sales ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_sales ON sales;
CREATE POLICY tenant_isolation_sales ON sales
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

-- ============================================================================
-- Table: deliveries
-- ============================================================================

CREATE TABLE IF NOT EXISTS deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Reference
    number VARCHAR(50) NOT NULL UNIQUE,
    sales_order_id UUID REFERENCES sales_orders(id) ON DELETE SET NULL,

    -- Dates
    ship_date DATE,
    delivery_date DATE,

    -- Status
    status delivery_status NOT NULL DEFAULT 'PENDING',

    -- Notes
    notes TEXT,

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_deliveries_tenant ON deliveries(tenant_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_number ON deliveries(number);
CREATE INDEX IF NOT EXISTS idx_deliveries_sales_order ON deliveries(sales_order_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_status ON deliveries(status);

COMMENT ON TABLE deliveries IS 'Delivery tracking for sales orders';

ALTER TABLE deliveries ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_deliveries ON deliveries;
CREATE POLICY tenant_isolation_deliveries ON deliveries
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

-- ============================================================================
-- Triggers
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'sales_orders_updated_at'
    ) THEN
        CREATE TRIGGER sales_orders_updated_at
            BEFORE UPDATE ON sales_orders
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'sales_updated_at'
    ) THEN
        CREATE TRIGGER sales_updated_at
            BEFORE UPDATE ON sales
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'deliveries_updated_at'
    ) THEN
        CREATE TRIGGER deliveries_updated_at
            BEFORE UPDATE ON deliveries
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END;
$$;

COMMIT;
