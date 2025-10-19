-- Rollback: 2025-10-18_120_pos_invoicing_link

BEGIN;

DROP INDEX IF EXISTS idx_pos_receipts_client_temp_id;
DROP INDEX IF EXISTS idx_pos_receipts_invoice_id;

ALTER TABLE pos_receipts 
DROP COLUMN IF EXISTS invoice_id,
DROP COLUMN IF EXISTS client_temp_id,
DROP COLUMN IF EXISTS metadata;

COMMIT;
