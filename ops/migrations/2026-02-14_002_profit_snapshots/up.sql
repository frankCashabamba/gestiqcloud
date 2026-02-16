-- Migration: 2026-02-14_002_profit_snapshots
-- Description: Profit Snapshots — Rentabilidad diaria + márgenes por producto

BEGIN;

-- profit_snapshots_daily: Dashboard rápido de rentabilidad diaria
CREATE TABLE IF NOT EXISTS profit_snapshots_daily (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    location_id UUID,
    total_sales NUMERIC(14,2) DEFAULT 0,
    total_cogs NUMERIC(14,2) DEFAULT 0,
    gross_profit NUMERIC(14,2) DEFAULT 0,
    total_expenses NUMERIC(14,2) DEFAULT 0,
    net_profit NUMERIC(14,2) DEFAULT 0,
    order_count INTEGER DEFAULT 0,
    item_count INTEGER DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_profit_snap_tenant_date_loc UNIQUE (tenant_id, date, location_id)
);

CREATE INDEX IF NOT EXISTS ix_profit_snapshots_daily_tenant_date ON profit_snapshots_daily(tenant_id, date);

-- product_profit_snapshots: Márgenes por producto/día
CREATE TABLE IF NOT EXISTS product_profit_snapshots (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    location_id UUID,
    revenue NUMERIC(14,2) DEFAULT 0,
    cogs NUMERIC(14,2) DEFAULT 0,
    gross_profit NUMERIC(14,2) DEFAULT 0,
    margin_pct NUMERIC(6,2) DEFAULT 0,
    sold_qty NUMERIC(14,3) DEFAULT 0,
    waste_qty NUMERIC(14,3) DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_prod_snap_tenant_date_prod_loc UNIQUE (tenant_id, date, product_id, location_id)
);

CREATE INDEX IF NOT EXISTS ix_product_profit_snapshots_tenant_date_product ON product_profit_snapshots(tenant_id, date, product_id);

COMMIT;
