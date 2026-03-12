-- Rollback: 2026-03-12_000_stock_items_expires_at

ALTER TABLE public.stock_items
    DROP COLUMN IF EXISTS expires_at;
