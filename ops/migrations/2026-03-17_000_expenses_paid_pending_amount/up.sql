-- Migration: 2026-03-17_000_expenses_paid_pending_amount
-- Adds paid_amount and pending_amount columns to the expenses table.
-- Idempotente: usa IF NOT EXISTS en todas las operaciones.

ALTER TABLE expenses
    ADD COLUMN IF NOT EXISTS paid_amount    NUMERIC(12, 2),
    ADD COLUMN IF NOT EXISTS pending_amount NUMERIC(12, 2);
