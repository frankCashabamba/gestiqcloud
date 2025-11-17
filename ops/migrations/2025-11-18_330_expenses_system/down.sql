-- Rollback: 2025-11-18_330_expenses_system

BEGIN;

DROP TRIGGER IF EXISTS expenses_updated_at ON expenses;

DROP POLICY IF EXISTS tenant_isolation_expenses ON expenses;

DROP TABLE IF EXISTS expenses CASCADE;

DROP TYPE IF EXISTS expense_status CASCADE;

DROP FUNCTION IF EXISTS update_updated_at_column();

COMMIT;
