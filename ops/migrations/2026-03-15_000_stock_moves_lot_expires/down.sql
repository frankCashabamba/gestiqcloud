-- Rollback: 2026-03-15_000_stock_moves_lot_expires

ALTER TABLE public.stock_moves
    DROP COLUMN IF EXISTS lot,
    DROP COLUMN IF EXISTS expires_at;
