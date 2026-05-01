-- Migration: 2026-05-01_002_accounting_periods (rollback)
BEGIN;
DROP INDEX IF EXISTS idx_accounting_periods_status;
DROP INDEX IF EXISTS idx_accounting_periods_tenant_year;
DROP TABLE IF EXISTS accounting_periods;
COMMIT;
