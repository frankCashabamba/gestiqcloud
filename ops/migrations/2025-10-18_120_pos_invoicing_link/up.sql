-- Migration: 2025-10-18_120_pos_invoicing_link
-- Description: Añadir invoice_id a pos_receipts y columnas adicionales

BEGIN;

-- Añadir invoice_id a pos_receipts si no existe
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'pos_receipts' AND column_name = 'invoice_id'
    ) THEN
        ALTER TABLE pos_receipts 
        ADD COLUMN invoice_id UUID REFERENCES invoices(id);
        
        CREATE INDEX idx_pos_receipts_invoice_id ON pos_receipts(invoice_id);
    END IF;
END $$;

-- Añadir metadata JSON para configuración offline
ALTER TABLE pos_receipts 
ADD COLUMN IF NOT EXISTS client_temp_id TEXT,
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

-- Índice para búsqueda por temp_id (idempotencia offline)
CREATE INDEX IF NOT EXISTS idx_pos_receipts_client_temp_id 
ON pos_receipts(client_temp_id) WHERE client_temp_id IS NOT NULL;

COMMIT;
