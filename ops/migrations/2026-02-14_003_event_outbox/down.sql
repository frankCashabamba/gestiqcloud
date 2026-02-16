-- Rollback: 2026-02-14_003_event_outbox

BEGIN;

DROP TABLE IF EXISTS event_outbox;

COMMIT;
