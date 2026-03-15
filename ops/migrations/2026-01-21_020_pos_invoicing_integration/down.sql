-- Reverse POS → Invoicing/Sales/Expenses integration columns

COMMENT ON COLUMN pos_receipts.invoice_id IS NULL;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'expenses' AND column_name = 'pos_receipt_id') THEN
        COMMENT ON COLUMN expenses.pos_receipt_id IS NULL;
    END IF;
END $$;

COMMENT ON COLUMN invoices.pos_receipt_id IS NULL;

DROP INDEX IF EXISTS idx_pos_receipts_invoice_id;
ALTER TABLE pos_receipts DROP COLUMN IF EXISTS invoice_id;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'expenses') THEN
        DROP INDEX IF EXISTS idx_expenses_pos_receipt_id;
        ALTER TABLE expenses DROP COLUMN IF EXISTS pos_receipt_id;
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sales_orders') THEN
        DROP INDEX IF EXISTS ux_sales_orders_tenant_pos_receipt_id;
        DROP INDEX IF EXISTS idx_sales_orders_pos_receipt_id;
        ALTER TABLE sales_orders DROP COLUMN IF EXISTS pos_receipt_id;
    END IF;
END $$;

DROP INDEX IF EXISTS idx_invoices_pos_receipt_id;
ALTER TABLE invoices DROP COLUMN IF EXISTS pos_receipt_id;
