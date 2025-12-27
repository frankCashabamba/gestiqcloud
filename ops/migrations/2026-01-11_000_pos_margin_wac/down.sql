BEGIN;

DROP INDEX IF EXISTS ix_stock_moves_tenant_wh_product_occurred;

DROP TABLE IF EXISTS inventory_cost_state;

ALTER TABLE pos_receipt_lines
    DROP COLUMN IF EXISTS gross_margin_pct,
    DROP COLUMN IF EXISTS gross_profit,
    DROP COLUMN IF EXISTS cogs_total,
    DROP COLUMN IF EXISTS cogs_unit,
    DROP COLUMN IF EXISTS net_total;

ALTER TABLE pos_receipts
    DROP COLUMN IF EXISTS warehouse_id;

ALTER TABLE stock_moves
    DROP COLUMN IF EXISTS occurred_at,
    DROP COLUMN IF EXISTS total_cost,
    DROP COLUMN IF EXISTS unit_cost;

COMMIT;
