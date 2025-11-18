-- ============================================================================
-- Migration: 2025-11-19_902_fix_enum_values (DOWN)
-- Description: Rollback ENUM recreation
-- ============================================================================

BEGIN;

-- Drop the corrected enum
DROP TYPE IF EXISTS sales_order_status CASCADE;

-- Recreate with original uppercase values
CREATE TYPE sales_order_status AS ENUM ('DRAFT', 'CONFIRMED', 'SHIPPED', 'DELIVERED', 'CANCELLED');

ALTER TABLE IF EXISTS sales_orders
  ALTER COLUMN status SET DEFAULT 'DRAFT'::sales_order_status;

COMMIT;
