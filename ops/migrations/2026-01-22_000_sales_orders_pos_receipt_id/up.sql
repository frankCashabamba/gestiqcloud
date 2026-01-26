-- Migration: Link sales_orders to pos_receipts
-- Date: 2026-01-22
-- Purpose: Add sales_orders.pos_receipt_id + indexes for POS↔CRM traceability

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sales_orders') THEN
        ALTER TABLE sales_orders
        ADD COLUMN IF NOT EXISTS pos_receipt_id UUID REFERENCES pos_receipts(id) ON DELETE SET NULL;

        CREATE INDEX IF NOT EXISTS idx_sales_orders_pos_receipt_id ON sales_orders(pos_receipt_id);

        -- Prevent duplicates when POS checkout retries.
        CREATE UNIQUE INDEX IF NOT EXISTS ux_sales_orders_tenant_pos_receipt_id
            ON sales_orders(tenant_id, pos_receipt_id) WHERE pos_receipt_id IS NOT NULL;
    END IF;
END $$;
