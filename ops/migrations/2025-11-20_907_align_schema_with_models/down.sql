-- Rollback: 2025-11-20_907_align_schema_with_models
-- Note: This is a destructive rollback. Use only if necessary.

BEGIN;

-- Rename columns back (this may fail if already reverted)
ALTER TABLE sales RENAME COLUMN IF EXISTS cliente_id TO customer_id;
ALTER TABLE sales RENAME COLUMN IF EXISTS fecha TO sale_date;
ALTER TABLE sales RENAME COLUMN IF EXISTS taxes TO tax;

-- Drop added columns
ALTER TABLE sales DROP COLUMN IF EXISTS notas;
ALTER TABLE sales DROP COLUMN IF EXISTS usuario_id;
ALTER TABLE sales DROP COLUMN IF EXISTS estado;

-- Drop indexes
DROP INDEX IF EXISTS idx_sales_cliente_id;
DROP INDEX IF EXISTS idx_sales_fecha;

COMMIT;
