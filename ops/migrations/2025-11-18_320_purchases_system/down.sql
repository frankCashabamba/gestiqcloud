-- Rollback: 2025-11-18_320_purchases_system

BEGIN;

DROP TRIGGER IF EXISTS purchases_updated_at ON purchases;

DROP POLICY IF EXISTS tenant_isolation_purchases ON purchases;

DROP TABLE IF EXISTS purchase_lines CASCADE;
DROP TABLE IF EXISTS purchases CASCADE;

DROP TYPE IF EXISTS purchase_status CASCADE;

DROP FUNCTION IF EXISTS update_updated_at_column();

COMMIT;
