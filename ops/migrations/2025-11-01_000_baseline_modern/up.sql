-- =====================================================
-- BASELINE MODERNA - GestiQCloud v2.0
-- Schema 100% Inglés - Fresh Start Nov 2025
-- =====================================================
-- 
-- Esta es la migración baseline consolidada que crea
-- el esquema completo moderno desde cero.
--
-- IMPORTANTE: Esta migración asume una BD limpia.
-- Las tablas auth_user y modulos_* deben existir previamente.
-- =====================================================

BEGIN;

-- =====================================================
-- CORE: Tenants (Multi-tenant principal)
-- =====================================================
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) UNIQUE,
    tax_id VARCHAR(30),
    phone VARCHAR(20),
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100),
    country_code CHAR(2) DEFAULT 'ES',
    website VARCHAR(255),
    base_currency CHAR(3) DEFAULT 'EUR',
    logo VARCHAR(500),
    primary_color VARCHAR(7) DEFAULT '#4f46e5',
    default_template VARCHAR(20) DEFAULT 'client',
    config_json JSONB DEFAULT '{}',
    active BOOLEAN DEFAULT TRUE,
    deactivation_reason VARCHAR(255),
    sector_id INTEGER,
    sector_template_name VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tenants_active ON tenants(active);
CREATE INDEX IF NOT EXISTS idx_tenants_slug ON tenants(slug);
CREATE INDEX IF NOT EXISTS idx_tenants_sector_id ON tenants(sector_id);

-- =====================================================
-- CATALOG: Product Categories
-- =====================================================
CREATE TABLE IF NOT EXISTS product_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    parent_id UUID REFERENCES product_categories(id) ON DELETE SET NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_product_categories_tenant ON product_categories(tenant_id);
CREATE INDEX IF NOT EXISTS idx_product_categories_parent ON product_categories(parent_id);

-- =====================================================
-- CATALOG: Products
-- =====================================================
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    sku VARCHAR(100),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price NUMERIC(12, 2),
    cost_price NUMERIC(12, 2),
    tax_rate NUMERIC(5, 2) DEFAULT 21.00,
    category VARCHAR(100),
    category_id UUID REFERENCES product_categories(id) ON DELETE SET NULL,
    active BOOLEAN DEFAULT TRUE,
    stock NUMERIC(14, 3) DEFAULT 0,
    unit VARCHAR(20) DEFAULT 'unit',
    product_metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_products_tenant ON products(tenant_id);
CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
CREATE INDEX IF NOT EXISTS idx_products_active ON products(active);
CREATE INDEX IF NOT EXISTS idx_products_category_id ON products(category_id);

-- RLS para products
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_products ON products;
CREATE POLICY tenant_isolation_products ON products
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

-- =====================================================
-- INVENTORY: Warehouses
-- =====================================================
CREATE TABLE IF NOT EXISTS warehouses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    address TEXT,
    active BOOLEAN DEFAULT TRUE,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, code)
);

CREATE INDEX IF NOT EXISTS idx_warehouses_tenant ON warehouses(tenant_id);
CREATE INDEX IF NOT EXISTS idx_warehouses_active ON warehouses(active);

-- =====================================================
-- INVENTORY: Stock Items
-- =====================================================
CREATE TABLE IF NOT EXISTS stock_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    warehouse_id UUID NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
    qty NUMERIC(14, 3) DEFAULT 0,
    location VARCHAR(50),
    lot VARCHAR(100),
    expires_at DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(warehouse_id, product_id, lot)
);

CREATE INDEX IF NOT EXISTS idx_stock_items_tenant ON stock_items(tenant_id);
CREATE INDEX IF NOT EXISTS idx_stock_items_warehouse ON stock_items(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_stock_items_product ON stock_items(product_id);

-- RLS para stock_items
ALTER TABLE stock_items ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_stock_items ON stock_items;
CREATE POLICY tenant_isolation_stock_items ON stock_items
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

-- =====================================================
-- INVENTORY: Stock Moves
-- =====================================================
CREATE TABLE IF NOT EXISTS stock_moves (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    warehouse_id UUID NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
    qty NUMERIC(12, 3) NOT NULL,
    kind VARCHAR(20) NOT NULL,
    ref_type VARCHAR(50),
    ref_id UUID,
    notes TEXT,
    posted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stock_moves_tenant ON stock_moves(tenant_id);
CREATE INDEX IF NOT EXISTS idx_stock_moves_product ON stock_moves(product_id);
CREATE INDEX IF NOT EXISTS idx_stock_moves_warehouse ON stock_moves(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_stock_moves_kind ON stock_moves(kind);
CREATE INDEX IF NOT EXISTS idx_stock_moves_posted_at ON stock_moves(posted_at);

-- =====================================================
-- ALERTS: Stock Alerts
-- =====================================================
CREATE TABLE IF NOT EXISTS stock_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    warehouse_id UUID REFERENCES warehouses(id) ON DELETE SET NULL,
    alert_type TEXT NOT NULL DEFAULT 'low_stock',
    threshold_config JSONB,
    current_qty INTEGER,
    threshold_qty INTEGER,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'acknowledged', 'resolved')),
    notified_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stock_alerts_tenant_status ON stock_alerts(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_stock_alerts_product ON stock_alerts(product_id);
CREATE INDEX IF NOT EXISTS idx_stock_alerts_warehouse ON stock_alerts(warehouse_id);

-- =====================================================
-- POS: Registers
-- =====================================================
CREATE TABLE IF NOT EXISTS pos_registers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    store_id UUID,
    name TEXT NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pos_registers_tenant ON pos_registers(tenant_id);

-- =====================================================
-- POS: Shifts
-- =====================================================
CREATE TABLE IF NOT EXISTS pos_shifts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    register_id UUID NOT NULL REFERENCES pos_registers(id) ON DELETE CASCADE,
    opened_by UUID NOT NULL,
    opened_at TIMESTAMPTZ DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    opening_float NUMERIC(12, 2) NOT NULL,
    closing_total NUMERIC(12, 2),
    status TEXT DEFAULT 'open' CHECK (status IN ('open', 'closed'))
);

CREATE INDEX IF NOT EXISTS idx_pos_shifts_register ON pos_shifts(register_id);
CREATE INDEX IF NOT EXISTS idx_pos_shifts_status ON pos_shifts(status);

-- =====================================================
-- POS: Receipts
-- =====================================================
CREATE TABLE IF NOT EXISTS pos_receipts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    register_id UUID NOT NULL REFERENCES pos_registers(id),
    shift_id UUID NOT NULL REFERENCES pos_shifts(id),
    number TEXT NOT NULL,
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'paid', 'voided', 'invoiced')),
    customer_id UUID,
    invoice_id UUID,
    gross_total NUMERIC(12, 2) NOT NULL,
    tax_total NUMERIC(12, 2) NOT NULL,
    currency CHAR(3) DEFAULT 'EUR',
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(register_id, shift_id, number)
);

CREATE INDEX IF NOT EXISTS idx_pos_receipts_tenant ON pos_receipts(tenant_id);
CREATE INDEX IF NOT EXISTS idx_pos_receipts_shift ON pos_receipts(shift_id);
CREATE INDEX IF NOT EXISTS idx_pos_receipts_status ON pos_receipts(status);

-- =====================================================
-- POS: Receipt Lines
-- =====================================================
CREATE TABLE IF NOT EXISTS pos_receipt_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    receipt_id UUID NOT NULL REFERENCES pos_receipts(id) ON DELETE CASCADE,
    product_id UUID NOT NULL,
    qty NUMERIC(12, 3) NOT NULL,
    uom VARCHAR(20) DEFAULT 'unit',
    unit_price NUMERIC(12, 4) NOT NULL,
    tax_rate NUMERIC(6, 4) NOT NULL DEFAULT 0.21,
    discount_pct NUMERIC(5, 2) DEFAULT 0,
    line_total NUMERIC(12, 2) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pos_receipt_lines_receipt ON pos_receipt_lines(receipt_id);
CREATE INDEX IF NOT EXISTS idx_pos_receipt_lines_product ON pos_receipt_lines(product_id);

-- =====================================================
-- POS: Payments
-- =====================================================
CREATE TABLE IF NOT EXISTS pos_payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    receipt_id UUID NOT NULL REFERENCES pos_receipts(id) ON DELETE CASCADE,
    method VARCHAR(50) NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    ref VARCHAR(255),
    paid_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pos_payments_receipt ON pos_payments(receipt_id);

-- =====================================================
-- AUTH: Refresh Tokens
-- =====================================================
CREATE TABLE IF NOT EXISTS auth_refresh_family (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    tenant_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    revoked_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_auth_refresh_family_user ON auth_refresh_family(user_id);

CREATE TABLE IF NOT EXISTS auth_refresh_token (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    family_id UUID NOT NULL REFERENCES auth_refresh_family(id) ON DELETE CASCADE,
    jti UUID,
    prev_jti UUID,
    token_hash VARCHAR(255),
    ua_hash VARCHAR(255),
    ip_hash VARCHAR(255),
    expires_at TIMESTAMPTZ,
    used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_auth_refresh_token_family ON auth_refresh_token(family_id);
CREATE INDEX IF NOT EXISTS idx_auth_refresh_token_jti ON auth_refresh_token(jti);
CREATE INDEX IF NOT EXISTS idx_auth_refresh_token_hash ON auth_refresh_token(token_hash);

-- =====================================================
-- FUNCTIONS: Stock Management
-- =====================================================
CREATE OR REPLACE FUNCTION check_low_stock()
RETURNS void AS $$
BEGIN
  INSERT INTO stock_alerts (
    tenant_id, product_id, warehouse_id,
    alert_type, current_qty, threshold_qty, status
  )
  SELECT DISTINCT ON (si.tenant_id, si.product_id, si.warehouse_id)
    si.tenant_id,
    si.product_id,
    si.warehouse_id,
    'low_stock',
    COALESCE(si.qty, 0)::INTEGER,
    COALESCE((p.product_metadata->>'reorder_point')::integer, 0) AS threshold_qty,
    'active'
  FROM stock_items si
  JOIN products p ON p.id = si.product_id
  WHERE
    COALESCE((p.product_metadata->>'reorder_point')::numeric, 0) > 0
    AND COALESCE(si.qty, 0) < COALESCE((p.product_metadata->>'reorder_point')::numeric, 0)
    AND NOT EXISTS (
      SELECT 1 FROM stock_alerts sa
      WHERE sa.tenant_id = si.tenant_id
        AND sa.product_id = si.product_id
        AND sa.warehouse_id = si.warehouse_id
        AND sa.status IN ('active', 'acknowledged')
        AND sa.created_at > NOW() - INTERVAL '24 hours'
    );

  UPDATE stock_alerts sa
  SET status = 'resolved', resolved_at = NOW()
  WHERE sa.status IN ('active', 'acknowledged')
    AND EXISTS (
      SELECT 1 FROM stock_items si
      JOIN products p ON p.id = si.product_id
      WHERE si.product_id = sa.product_id
        AND si.warehouse_id = sa.warehouse_id
        AND COALESCE(si.qty, 0) >= COALESCE((p.product_metadata->>'reorder_point')::numeric, 0)
        AND COALESCE((p.product_metadata->>'reorder_point')::numeric, 0) > 0
    );
END;
$$ LANGUAGE plpgsql;

COMMIT;
