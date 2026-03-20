-- Migration: 2026-03-20_005_stock_items_consolidate_duplicates
-- Purpose: Merge duplicate stock_items rows with same (tenant_id, warehouse_id, product_id, lot, expires_at)
--          and add a unique index to prevent future duplicates.
--
-- Root cause: no UNIQUE constraint existed, so multiple purchase receptions or adjustments
-- could create separate rows for the same product/warehouse/lot combination instead of
-- updating the existing one. This caused the POS to show a redundant lot-selection dialog.

-- Step 1: Update the keeper row (rn=1) with the summed qty of all duplicates in that group.
UPDATE stock_items si
SET qty = agg.total_qty
FROM (
    SELECT
        id,
        SUM(qty) OVER (
            PARTITION BY tenant_id, warehouse_id, product_id,
                         COALESCE(lot, ''), COALESCE(expires_at, '0001-01-01'::DATE)
        ) AS total_qty,
        ROW_NUMBER() OVER (
            PARTITION BY tenant_id, warehouse_id, product_id,
                         COALESCE(lot, ''), COALESCE(expires_at, '0001-01-01'::DATE)
            ORDER BY id::text
        ) AS rn,
        COUNT(*) OVER (
            PARTITION BY tenant_id, warehouse_id, product_id,
                         COALESCE(lot, ''), COALESCE(expires_at, '0001-01-01'::DATE)
        ) AS cnt
    FROM stock_items
) agg
WHERE si.id = agg.id
  AND agg.rn = 1
  AND agg.cnt > 1;

-- Step 2: Delete all duplicate rows except the keeper (rn=1).
DELETE FROM stock_items
WHERE id IN (
    SELECT id FROM (
        SELECT
            id,
            ROW_NUMBER() OVER (
                PARTITION BY tenant_id, warehouse_id, product_id,
                             COALESCE(lot, ''), COALESCE(expires_at, '0001-01-01'::DATE)
                ORDER BY id::text
            ) AS rn
        FROM stock_items
    ) ranked
    WHERE rn > 1
);

-- Step 3: Unique functional index to prevent future duplicates.
-- COALESCE maps NULL lot -> '' and NULL expires_at -> '0001-01-01' so that
-- two "sin lote / sin caducidad" rows for the same product/warehouse are rejected.
CREATE UNIQUE INDEX IF NOT EXISTS uq_stock_items_identity
    ON stock_items (
        tenant_id,
        warehouse_id,
        product_id,
        COALESCE(lot, ''),
        COALESCE(expires_at, '0001-01-01'::DATE)
    );
