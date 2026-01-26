-- Rollback: Link sales_orders to pos_receipts

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sales_orders') THEN
        DROP INDEX IF EXISTS ux_sales_orders_tenant_pos_receipt_id;
        DROP INDEX IF EXISTS idx_sales_orders_pos_receipt_id;
        ALTER TABLE sales_orders DROP COLUMN IF EXISTS pos_receipt_id;
    END IF;
END $$;

