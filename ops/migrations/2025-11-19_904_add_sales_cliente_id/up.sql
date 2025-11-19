-- Migration: 2025-11-19_904_add_sales_cliente_id
-- Description: Add cliente_id field to sales table

BEGIN;

ALTER TABLE sales
    ADD COLUMN IF NOT EXISTS cliente_id UUID REFERENCES clients(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_sales_cliente_id ON sales(cliente_id);

COMMIT;
