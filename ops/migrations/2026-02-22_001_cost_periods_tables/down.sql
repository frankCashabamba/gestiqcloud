-- Rollback: 2026-02-22_001_cost_periods_tables

BEGIN;

DROP TABLE IF EXISTS cost_period_validations;
DROP TABLE IF EXISTS cost_periods;

COMMIT;
