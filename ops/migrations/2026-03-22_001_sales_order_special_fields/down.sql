ALTER TABLE sales_orders
  DROP COLUMN IF EXISTS deposit_amount,
  DROP COLUMN IF EXISTS deposit_paid,
  DROP COLUMN IF EXISTS payment_method;
