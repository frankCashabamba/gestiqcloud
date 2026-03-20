-- Rollback: 2026-03-20_005_stock_items_consolidate_duplicates
-- Note: the duplicate rows that were merged CANNOT be restored (data loss by design).
-- This only removes the unique index.

DROP INDEX IF EXISTS uq_stock_items_identity;
