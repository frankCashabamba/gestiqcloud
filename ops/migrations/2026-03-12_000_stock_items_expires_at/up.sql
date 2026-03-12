-- Migration: 2026-03-12_000_stock_items_expires_at
-- Purpose: Add expires_at column to stock_items for ingredient expiry tracking

ALTER TABLE public.stock_items
    ADD COLUMN IF NOT EXISTS expires_at DATE;
