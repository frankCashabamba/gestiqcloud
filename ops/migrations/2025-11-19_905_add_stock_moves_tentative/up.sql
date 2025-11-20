-- Migration: 2025-11-19_905_add_stock_moves_tentative
-- Description: Add tentative field to stock_moves table

BEGIN;

ALTER TABLE IF EXISTS stock_moves
    ADD COLUMN IF NOT EXISTS tentative BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_stock_moves_tentative ON stock_moves(tentative);

COMMIT;
