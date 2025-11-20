-- ============================================================================
-- Migration Rollback: 2025-11-03_202_finance_caja
-- Description: Rollback of cash management system
-- ============================================================================

-- Drop triggers
DROP TRIGGER IF EXISTS cash_movements_updated_at ON cash_movements;
DROP TRIGGER IF EXISTS cash_closings_updated_at ON cash_closings;

-- Drop RLS policies
DROP POLICY IF EXISTS cash_movements_tenant_isolation ON cash_movements;
DROP POLICY IF EXISTS cash_closings_tenant_isolation ON cash_closings;

-- Drop tables (in reverse order of dependencies)
DROP TABLE IF EXISTS cash_movements CASCADE;
DROP TABLE IF EXISTS cash_closings CASCADE;

-- Drop ENUM types
DROP TYPE IF EXISTS cash_movement_type CASCADE;
DROP TYPE IF EXISTS cash_movement_category CASCADE;
DROP TYPE IF EXISTS cash_closing_status CASCADE;

-- Drop functions
DROP FUNCTION IF EXISTS update_updated_at_column();
