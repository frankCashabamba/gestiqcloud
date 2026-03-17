-- Rollback: 2026-03-17_000_expenses_paid_pending_amount
ALTER TABLE expenses
    DROP COLUMN IF EXISTS paid_amount,
    DROP COLUMN IF EXISTS pending_amount;
