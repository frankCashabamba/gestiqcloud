-- Migration: 2026-01-11_000_pos_margin_wac
-- Description: WAC cost state + POS margin snapshots + stock move costs.

BEGIN;

ALTER TABLE stock_moves
    ADD COLUMN IF NOT EXISTS unit_cost NUMERIC(12, 6),
    ADD COLUMN IF NOT EXISTS total_cost NUMERIC(14, 6),
    ADD COLUMN IF NOT EXISTS occurred_at TIMESTAMPTZ NOT NULL DEFAULT now();

ALTER TABLE pos_receipts
    ADD COLUMN IF NOT EXISTS warehouse_id UUID;

ALTER TABLE pos_receipt_lines
    ADD COLUMN IF NOT EXISTS net_total NUMERIC(12, 2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS cogs_unit NUMERIC(12, 6) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS cogs_total NUMERIC(12, 2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS gross_profit NUMERIC(12, 2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS gross_margin_pct NUMERIC(7, 4) NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS inventory_cost_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    warehouse_id UUID NOT NULL,
    product_id UUID NOT NULL,
    on_hand_qty NUMERIC NOT NULL DEFAULT 0,
    avg_cost NUMERIC(12, 6) NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, warehouse_id, product_id)
);

CREATE INDEX IF NOT EXISTS ix_stock_moves_tenant_wh_product_occurred
    ON stock_moves(tenant_id, warehouse_id, product_id, occurred_at);

COMMIT;
