-- Rollback: 2025-10-18_121_store_credits

BEGIN;

DROP TRIGGER IF EXISTS trg_store_credits_updated_at ON store_credits;
DROP FUNCTION IF EXISTS update_store_credit_timestamp();
DROP FUNCTION IF EXISTS generate_store_credit_code();

DROP TABLE IF EXISTS store_credit_events CASCADE;
DROP TABLE IF EXISTS store_credits CASCADE;

COMMIT;
