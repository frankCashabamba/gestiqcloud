-- Migration: Add pos_receipt_id column to sales_orders table
-- Description: Link sales orders back to their source POS receipts
-- Date: 2025-01-22

BEGIN;

ALTER TABLE sales_orders
ADD COLUMN IF NOT EXISTS pos_receipt_id UUID;

-- Add foreign key constraint if pos_receipts table exists
ALTER TABLE sales_orders
ADD CONSTRAINT fk_sales_orders_pos_receipt_id
FOREIGN KEY (pos_receipt_id)
REFERENCES pos_receipts(id)
ON DELETE SET NULL;

COMMIT;
