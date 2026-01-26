-- Migration: POS → Invoicing/Sales/Expenses Integration
-- Date: 2026-01-21
-- Purpose: Add foreign key references to link POS receipts with invoices, sales, and expenses

-- ============================================================
-- 1. Add pos_receipt_id column to invoices table
-- ============================================================
ALTER TABLE invoices
ADD COLUMN IF NOT EXISTS pos_receipt_id UUID REFERENCES pos_receipts(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_invoices_pos_receipt_id ON invoices(pos_receipt_id);

-- ============================================================
-- 2. Add pos_receipt_id column to sales table
-- ============================================================
-- Removed: legacy `sales` table no longer used

-- ============================================================
-- 2b. Add pos_receipt_id column to sales_orders table (CRM/ventas)
-- ============================================================
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sales_orders') THEN
        ALTER TABLE sales_orders
        ADD COLUMN IF NOT EXISTS pos_receipt_id UUID REFERENCES pos_receipts(id) ON DELETE SET NULL;

        CREATE INDEX IF NOT EXISTS idx_sales_orders_pos_receipt_id ON sales_orders(pos_receipt_id);
        CREATE UNIQUE INDEX IF NOT EXISTS ux_sales_orders_tenant_pos_receipt_id
            ON sales_orders(tenant_id, pos_receipt_id) WHERE pos_receipt_id IS NOT NULL;
    END IF;
END $$;

-- ============================================================
-- 3. Add pos_receipt_id column to expenses table
-- ============================================================
-- First check if expenses table exists and has the column
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'expenses') THEN
        ALTER TABLE expenses
        ADD COLUMN IF NOT EXISTS pos_receipt_id UUID REFERENCES pos_receipts(id) ON DELETE SET NULL;

        CREATE INDEX IF NOT EXISTS idx_expenses_pos_receipt_id ON expenses(pos_receipt_id);
    END IF;
END $$;

-- ============================================================
-- 4. Add invoice_id column to pos_receipts (if not exists)
-- ============================================================
ALTER TABLE pos_receipts
ADD COLUMN IF NOT EXISTS invoice_id UUID REFERENCES invoices(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_pos_receipts_invoice_id ON pos_receipts(invoice_id);

-- ============================================================
-- 5. Log migration completion
-- ============================================================
-- This is optional but helpful for tracking
COMMENT ON COLUMN invoices.pos_receipt_id IS 'Link to POS receipt for invoices created from POS sales';
COMMENT ON COLUMN expenses.pos_receipt_id IS 'Link to POS receipt for expenses (refunds/returns) from POS sales';
COMMENT ON COLUMN pos_receipts.invoice_id IS 'Link to formal invoice created from this receipt';
