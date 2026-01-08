ALTER TABLE pos_receipts
ADD COLUMN IF NOT EXISTS cashier_id UUID;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'pos_receipts_cashier_id_fkey'
    ) THEN
        ALTER TABLE pos_receipts
        ADD CONSTRAINT pos_receipts_cashier_id_fkey
        FOREIGN KEY (cashier_id)
        REFERENCES company_users(id)
        ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_pos_receipts_cashier_id
ON pos_receipts(cashier_id);
