-- Migration: 2025-11-19_904_add_sales_cliente_id (ROLLBACK)

BEGIN;

ALTER TABLE sales
    DROP COLUMN IF EXISTS cliente_id;

COMMIT;
