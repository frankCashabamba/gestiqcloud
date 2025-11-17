-- =====================================================
-- ROLLBACK: POS Extensions
-- =====================================================

BEGIN;

DROP TABLE IF EXISTS store_credit_events CASCADE;
DROP TABLE IF EXISTS store_credits CASCADE;

COMMIT;
