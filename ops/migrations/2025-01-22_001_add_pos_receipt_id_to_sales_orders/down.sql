-- Rollback: Remove pos_receipt_id column from sales_orders

BEGIN;

ALTER TABLE sales_orders
DROP CONSTRAINT IF EXISTS fk_sales_orders_pos_receipt_id;

ALTER TABLE sales_orders
DROP COLUMN IF EXISTS pos_receipt_id;

COMMIT;
