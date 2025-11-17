-- =====================================================
-- ROLLBACK: E-Invoicing Tables
-- =====================================================

BEGIN;

DROP TABLE IF EXISTS sii_batch_items CASCADE;
DROP TABLE IF EXISTS sii_batches CASCADE;
DROP TABLE IF EXISTS sri_submissions CASCADE;
DROP TABLE IF EXISTS einv_credentials CASCADE;

DROP TYPE IF EXISTS sii_item_status;
DROP TYPE IF EXISTS sii_batch_status;
DROP TYPE IF EXISTS sri_status;

COMMIT;
