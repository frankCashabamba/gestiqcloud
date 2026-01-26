-- Rollback: Remove `pos_invoice_lines` table

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pos_invoice_lines') THEN
        DROP INDEX IF EXISTS idx_pos_invoice_lines_pos_receipt_line_id;
        DROP TABLE IF EXISTS pos_invoice_lines CASCADE;
    END IF;
END $$;
