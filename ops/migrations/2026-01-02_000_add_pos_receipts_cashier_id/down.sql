ALTER TABLE pos_receipts
DROP CONSTRAINT IF EXISTS pos_receipts_cashier_id_fkey;

DROP INDEX IF EXISTS ix_pos_receipts_cashier_id;

ALTER TABLE pos_receipts
DROP COLUMN IF EXISTS cashier_id;
