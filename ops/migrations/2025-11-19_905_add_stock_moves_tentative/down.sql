-- Migration: 2025-11-19_905_add_stock_moves_tentative (ROLLBACK)

BEGIN;

ALTER TABLE stock_moves
    DROP COLUMN IF EXISTS tentative;

COMMIT;
