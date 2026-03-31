-- Rollback: 2026-03-31_001_promotions
BEGIN;

DROP POLICY IF EXISTS promotions_tenant_isolation ON promotions;
DROP TABLE IF EXISTS promotions;

COMMIT;
