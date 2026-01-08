-- Migration: 2026-01-12_000_pos_receipts_backfill_wh
-- Description: Backfill pos_receipts.warehouse_id from stock_moves.

BEGIN;

UPDATE pos_receipts r
SET warehouse_id = sm.warehouse_id
FROM (
    SELECT ref_id::uuid AS receipt_id, MIN(warehouse_id::text)::uuid AS warehouse_id
    FROM stock_moves
    WHERE ref_type IN ('pos_receipt', 'pos_receipt_refund')
    GROUP BY ref_id
) sm
WHERE r.warehouse_id IS NULL
  AND r.id = sm.receipt_id;

COMMIT;
