-- Campos para pedidos especiales (panadería, taller, etc.)
-- required_date ya existe y se usa como delivery_date
ALTER TABLE sales_orders
  ADD COLUMN IF NOT EXISTS deposit_amount  NUMERIC(12, 2) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS deposit_paid    BOOLEAN        NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS payment_method  VARCHAR(50);
