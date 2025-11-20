-- =====================================================
-- Migration: 2025-11-19_901_pos_items_table
-- Description: Create pos_items table for POS receipts
-- =====================================================

BEGIN;

-- =====================================================
-- POS_ITEMS: Line items in POS receipts
-- =====================================================
CREATE TABLE IF NOT EXISTS pos_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    receipt_id UUID NOT NULL,
    product_id UUID NOT NULL,
    qty NUMERIC(12, 4) NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL,
    tax NUMERIC(12, 2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    FOREIGN KEY (receipt_id) REFERENCES pos_receipts(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_pos_items_receipt_id ON pos_items(receipt_id);
CREATE INDEX IF NOT EXISTS idx_pos_items_product_id ON pos_items(product_id);

COMMIT;
