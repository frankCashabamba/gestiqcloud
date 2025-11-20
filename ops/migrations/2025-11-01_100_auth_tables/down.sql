-- =====================================================
-- ROLLBACK: AUTH TABLES
-- =====================================================

BEGIN;

DROP TABLE IF EXISTS auth_audit CASCADE;
DROP TABLE IF EXISTS auth_refresh_token CASCADE;
DROP TABLE IF EXISTS auth_refresh_family CASCADE;
DROP TABLE IF EXISTS auth_user CASCADE;

COMMIT;
