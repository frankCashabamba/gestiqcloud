-- Migration: 2026-03-15_000_stock_moves_lot_expires
-- Purpose: Add lot and expires_at columns to stock_moves for traceability

ALTER TABLE public.stock_moves
    ADD COLUMN IF NOT EXISTS lot VARCHAR(100),
    ADD COLUMN IF NOT EXISTS expires_at DATE;
