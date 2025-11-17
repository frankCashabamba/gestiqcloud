-- Rollback: 2025-11-01_165_add_incident_assigned_fk

BEGIN;

ALTER TABLE incidents DROP CONSTRAINT IF EXISTS fk_incidents_assigned_to;

COMMIT;
