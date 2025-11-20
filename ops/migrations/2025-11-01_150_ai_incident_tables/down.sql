-- =====================================================
-- ROLLBACK: AI Incident Tables
-- =====================================================

BEGIN;

DROP TABLE IF EXISTS notification_log CASCADE;
DROP TABLE IF EXISTS notification_channels CASCADE;
DROP TABLE IF EXISTS incidents CASCADE;

COMMIT;
