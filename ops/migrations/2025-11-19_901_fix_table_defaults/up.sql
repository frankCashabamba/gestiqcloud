-- ============================================================================
-- Migration: 2025-11-19_901_fix_table_defaults
-- Description: Ensure correct defaults for PostgreSQL native functions
-- ============================================================================

BEGIN;

-- Ensure pos_registers.id has gen_random_uuid() default
-- Must DROP constraints first if they exist, then recreate
ALTER TABLE IF EXISTS pos_registers
  DROP CONSTRAINT IF EXISTS pos_registers_pkey CASCADE;

ALTER TABLE IF EXISTS pos_registers
  ALTER COLUMN id SET DEFAULT gen_random_uuid();

-- Recreate primary key if table exists
ALTER TABLE IF EXISTS pos_registers
  ADD CONSTRAINT pos_registers_pkey PRIMARY KEY (id);

-- Same for other UUID primary keys
ALTER TABLE IF EXISTS sales_orders
  ALTER COLUMN id SET DEFAULT gen_random_uuid();

ALTER TABLE IF EXISTS sales_order_items
  ALTER COLUMN id SET DEFAULT gen_random_uuid();

ALTER TABLE IF EXISTS sales
  ALTER COLUMN id SET DEFAULT gen_random_uuid();

ALTER TABLE IF EXISTS deliveries
  ALTER COLUMN id SET DEFAULT gen_random_uuid();

COMMIT;
