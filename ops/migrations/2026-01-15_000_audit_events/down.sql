BEGIN;

DROP INDEX IF EXISTS ix_audit_events_created_at;
DROP INDEX IF EXISTS ix_audit_events_action;
DROP INDEX IF EXISTS ix_audit_events_entity;
DROP INDEX IF EXISTS ix_audit_events_tenant_id;
DROP TABLE IF EXISTS audit_events;

COMMIT;
