-- =====================================================
-- ROLLBACK: Config Tables
-- =====================================================

BEGIN;

DROP TABLE IF EXISTS doc_series CASCADE;
DROP TABLE IF EXISTS base_roles CASCADE;

COMMIT;
