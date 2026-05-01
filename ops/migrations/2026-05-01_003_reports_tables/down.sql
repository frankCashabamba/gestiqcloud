-- Rollback for 2026-05-01_003_reports_tables.
BEGIN;

DROP POLICY IF EXISTS scheduled_reports_tenant_isolation ON scheduled_reports;
DROP POLICY IF EXISTS reports_tenant_isolation ON reports;

DROP INDEX IF EXISTS ix_scheduled_reports_due;
DROP INDEX IF EXISTS ix_scheduled_reports_tenant;
DROP INDEX IF EXISTS ix_reports_tenant_type;
DROP INDEX IF EXISTS ix_reports_tenant_created;

DROP TABLE IF EXISTS scheduled_reports;
DROP TABLE IF EXISTS reports;

COMMIT;
