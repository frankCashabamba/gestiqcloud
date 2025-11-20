-- =====================================================
-- ROLLBACK: Core Business Tables
-- =====================================================

BEGIN;

DROP TABLE IF EXISTS invoice_lines CASCADE;
DROP TABLE IF EXISTS invoices CASCADE;
DROP TABLE IF EXISTS clients CASCADE;

COMMIT;
