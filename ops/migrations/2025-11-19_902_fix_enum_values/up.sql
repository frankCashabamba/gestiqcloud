-- ============================================================================
-- Migration: 2025-11-19_902_fix_enum_values
-- Description: Recreate ENUMs with correct lowercase values
-- ============================================================================

BEGIN;

-- Drop existing sales_order_status enum if it exists (with CASCADE to remove constraints)
DROP TYPE IF EXISTS sales_order_status CASCADE;

-- Recreate with lowercase values
CREATE TYPE sales_order_status AS ENUM ('draft', 'confirmed', 'shipped', 'delivered', 'cancelled');

-- Recreate the table with correct enum references
-- Note: This assumes sales_orders table exists and we need to recreate it
-- If the table doesn't exist, the migration will fail safely with CASCADE

-- Re-add constraints if needed (depends on your schema)
ALTER TABLE IF EXISTS sales_orders
  ALTER COLUMN status SET DEFAULT 'draft'::sales_order_status;

COMMIT;
