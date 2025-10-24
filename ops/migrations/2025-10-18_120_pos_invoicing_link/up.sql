-- Migration: 2025-10-18_120_pos_invoicing_link
-- Description: Link POS receipts to invoices (or add column without FK if invoices not present) and add metadata fields.

BEGIN;

-- Add invoice_id to pos_receipts if missing. If public.invoices doesn't exist yet in this branch,
-- create the column without a foreign key. A later migration can attach the FK when invoices exists.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'pos_receipts'
          AND column_name = 'invoice_id'
    ) THEN
        IF to_regclass('public.invoices') IS NOT NULL THEN
            ALTER TABLE public.pos_receipts
            ADD COLUMN invoice_id uuid REFERENCES public.invoices(id);
        ELSE
            ALTER TABLE public.pos_receipts
            ADD COLUMN invoice_id uuid;
        END IF;

        -- Create index if not exists
        IF NOT EXISTS (
            SELECT 1
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relname = 'idx_pos_receipts_invoice_id'
              AND n.nspname = 'public'
        ) THEN
            CREATE INDEX idx_pos_receipts_invoice_id ON public.pos_receipts(invoice_id);
        END IF;
    END IF;
END $$;

-- Add metadata columns for offline/idempotency support
ALTER TABLE public.pos_receipts
    ADD COLUMN IF NOT EXISTS client_temp_id text,
    ADD COLUMN IF NOT EXISTS metadata jsonb DEFAULT '{}'::jsonb;

-- Partial index for quick lookup by client_temp_id
CREATE INDEX IF NOT EXISTS idx_pos_receipts_client_temp_id
ON public.pos_receipts(client_temp_id)
WHERE client_temp_id IS NOT NULL;

COMMIT;

