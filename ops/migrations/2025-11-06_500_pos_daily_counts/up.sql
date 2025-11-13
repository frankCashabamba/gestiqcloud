-- =====================================================
-- POS: Daily Counts Table
-- =====================================================
-- Table to store daily cash register counts for bakery accounting
-- Tracks opening float, sales totals, closing cash, and discrepancies

CREATE TABLE IF NOT EXISTS pos_daily_counts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    register_id UUID NOT NULL REFERENCES pos_registers(id) ON DELETE CASCADE,
    shift_id UUID NOT NULL REFERENCES pos_shifts(id) ON DELETE CASCADE,
    count_date DATE NOT NULL,
    opening_float NUMERIC(12, 2) NOT NULL DEFAULT 0,
    cash_sales NUMERIC(12, 2) NOT NULL DEFAULT 0,
    card_sales NUMERIC(12, 2) NOT NULL DEFAULT 0,
    other_sales NUMERIC(12, 2) NOT NULL DEFAULT 0,
    total_sales NUMERIC(12, 2) NOT NULL DEFAULT 0,
    expected_cash NUMERIC(12, 2) NOT NULL DEFAULT 0,
    counted_cash NUMERIC(12, 2) NOT NULL DEFAULT 0,
    discrepancy NUMERIC(12, 2) NOT NULL DEFAULT 0,
    loss_amount NUMERIC(12, 2) DEFAULT 0,
    loss_note TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(register_id, count_date)
);

CREATE INDEX IF NOT EXISTS idx_pos_daily_counts_tenant ON pos_daily_counts(tenant_id);
CREATE INDEX IF NOT EXISTS idx_pos_daily_counts_register ON pos_daily_counts(register_id);
CREATE INDEX IF NOT EXISTS idx_pos_daily_counts_date ON pos_daily_counts(count_date);
CREATE INDEX IF NOT EXISTS idx_pos_daily_counts_shift ON pos_daily_counts(shift_id);

-- RLS for pos_daily_counts
ALTER TABLE pos_daily_counts ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_pos_daily_counts ON pos_daily_counts;
CREATE POLICY tenant_isolation_pos_daily_counts ON pos_daily_counts
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));
