-- ============================================================================
-- Migration: 2025-11-03_202_finance_caja
-- Description: Complete cash management system with movements and daily closings
-- Updated: 2025-11-17 - Spanish to English names
-- ============================================================================

-- Create helper function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create ENUM types for cash
DO $$ BEGIN
  CREATE TYPE cash_movement_type AS ENUM ('INCOME', 'EXPENSE', 'ADJUSTMENT');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE cash_movement_category AS ENUM (
    'SALES',
    'PURCHASES',
    'EXPENSE',
    'PAYROLL',
    'BANK',
    'CHANGE',
    'ADJUSTMENT',
    'OTHER'
  );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE cash_closing_status AS ENUM ('OPEN', 'CLOSED', 'PENDING');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

COMMENT ON TYPE cash_movement_type IS 'Movement type: INCOME=Cash in, EXPENSE=Cash out, ADJUSTMENT=Reconciliation adjustment';
COMMENT ON TYPE cash_movement_category IS 'Movement category: SALES, PURCHASES, EXPENSE, PAYROLL, BANK, CHANGE, ADJUSTMENT, OTHER';
COMMENT ON TYPE cash_closing_status IS 'Closing status: OPEN=In progress, CLOSED=Reconciled, PENDING=With discrepancy';

-- ============================================================================
-- Table: cash_movements
-- ============================================================================

CREATE TABLE IF NOT EXISTS cash_movements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Type and category
    type cash_movement_type NOT NULL,
    category cash_movement_category NOT NULL,

    -- Amount
    amount NUMERIC(12, 2) NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'EUR',

    -- Description
    description VARCHAR(255) NOT NULL,
    notes TEXT,

    -- Reference to source document
    ref_doc_type VARCHAR(50),
    ref_doc_id UUID,

    -- Multi-cash (optional)
    cash_box_id UUID,

    -- Responsible user
    user_id UUID,

    -- Date
    date DATE NOT NULL,

    -- Relation to closing
    closing_id UUID,

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_cash_movements_tenant_id ON cash_movements(tenant_id);
CREATE INDEX IF NOT EXISTS idx_cash_movements_date ON cash_movements(date);
CREATE INDEX IF NOT EXISTS idx_cash_movements_type ON cash_movements(type);
CREATE INDEX IF NOT EXISTS idx_cash_movements_category ON cash_movements(category);
CREATE INDEX IF NOT EXISTS idx_cash_movements_cash_box_id ON cash_movements(cash_box_id) WHERE cash_box_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_cash_movements_closing_id ON cash_movements(closing_id) WHERE closing_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_cash_movements_ref_doc ON cash_movements(ref_doc_type, ref_doc_id) WHERE ref_doc_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_cash_movements_date_tenant ON cash_movements(date, tenant_id);

-- Comments
COMMENT ON TABLE cash_movements IS 'Cash movements (income, expenses, adjustments)';
COMMENT ON COLUMN cash_movements.type IS 'INCOME (positive), EXPENSE (negative), ADJUSTMENT';
COMMENT ON COLUMN cash_movements.category IS 'Movement category (SALES, PURCHASES, EXPENSE, etc.)';
COMMENT ON COLUMN cash_movements.amount IS 'Amount (positive for income, negative for expenses)';
COMMENT ON COLUMN cash_movements.currency IS 'Currency code ISO 4217 (EUR, USD, etc.)';
COMMENT ON COLUMN cash_movements.description IS 'Movement description';
COMMENT ON COLUMN cash_movements.ref_doc_type IS 'Source document type (invoice, receipt, expense, payroll)';
COMMENT ON COLUMN cash_movements.ref_doc_id IS 'ID of source document';
COMMENT ON COLUMN cash_movements.cash_box_id IS 'ID of cash box (for multi-cash/multi-point)';
COMMENT ON COLUMN cash_movements.user_id IS 'User who recorded the movement';
COMMENT ON COLUMN cash_movements.closing_id IS 'ID of the closing this belongs to';

-- ============================================================================
-- Table: cash_closings
-- ============================================================================

CREATE TABLE IF NOT EXISTS cash_closings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Date and cash box
    date DATE NOT NULL,
    cash_box_id UUID,
    currency CHAR(3) NOT NULL DEFAULT 'EUR',

    -- === BALANCES ===
    opening_balance NUMERIC(12, 2) NOT NULL DEFAULT 0,
    total_income NUMERIC(12, 2) NOT NULL DEFAULT 0,
    total_expenses NUMERIC(12, 2) NOT NULL DEFAULT 0,
    theoretical_balance NUMERIC(12, 2) NOT NULL DEFAULT 0,
    actual_balance NUMERIC(12, 2) NOT NULL DEFAULT 0,
    difference NUMERIC(12, 2) NOT NULL DEFAULT 0,

    -- === STATUS ===
    status cash_closing_status NOT NULL DEFAULT 'OPEN',
    is_balanced BOOLEAN NOT NULL DEFAULT FALSE,

    -- === DETAILS ===
    bills_details JSONB,
    notes TEXT,

    -- === USERS ===
    opened_by UUID,
    opened_at TIMESTAMPTZ,
    closed_by UUID,
    closed_at TIMESTAMPTZ,

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- === CONSTRAINTS ===
    CONSTRAINT cash_closings_date_cash_box_unique
        UNIQUE (tenant_id, date, cash_box_id),
    CONSTRAINT cash_closings_balances_check
        CHECK (theoretical_balance = opening_balance + total_income - total_expenses),
    CONSTRAINT cash_closings_difference_check
        CHECK (difference = actual_balance - theoretical_balance)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_cash_closings_tenant_id ON cash_closings(tenant_id);
CREATE INDEX IF NOT EXISTS idx_cash_closings_date ON cash_closings(date);
CREATE INDEX IF NOT EXISTS idx_cash_closings_status ON cash_closings(status);
CREATE INDEX IF NOT EXISTS idx_cash_closings_cash_box_id ON cash_closings(cash_box_id) WHERE cash_box_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_cash_closings_is_balanced ON cash_closings(is_balanced) WHERE is_balanced = FALSE;
CREATE INDEX IF NOT EXISTS idx_cash_closings_date_tenant ON cash_closings(date, tenant_id);

-- Comments
COMMENT ON TABLE cash_closings IS 'Daily cash closings with reconciliation';
COMMENT ON COLUMN cash_closings.date IS 'Date of closing';
COMMENT ON COLUMN cash_closings.cash_box_id IS 'ID of cash box (for multi-cash)';
COMMENT ON COLUMN cash_closings.opening_balance IS 'Balance at start of day';
COMMENT ON COLUMN cash_closings.total_income IS 'Sum of income for the day';
COMMENT ON COLUMN cash_closings.total_expenses IS 'Sum of expenses for the day (absolute value)';
COMMENT ON COLUMN cash_closings.theoretical_balance IS 'Theoretical balance (opening + income - expenses)';
COMMENT ON COLUMN cash_closings.actual_balance IS 'Cash physically counted';
COMMENT ON COLUMN cash_closings.difference IS 'Difference (actual - theoretical)';
COMMENT ON COLUMN cash_closings.status IS 'Status: OPEN, CLOSED, PENDING';
COMMENT ON COLUMN cash_closings.is_balanced IS 'True if difference = 0';
COMMENT ON COLUMN cash_closings.bills_details IS 'Breakdown of bills and coins counted (JSON)';

-- Add FK constraint for closing_id after both tables are created
DO $$ BEGIN
    ALTER TABLE cash_movements
    ADD CONSTRAINT fk_cash_movements_closing
    FOREIGN KEY (closing_id) REFERENCES cash_closings(id) ON DELETE SET NULL;
EXCEPTION WHEN OTHERS THEN
    NULL; -- Constraint already exists
END $$;

-- ============================================================================
-- RLS (Row Level Security)
-- ============================================================================

ALTER TABLE cash_movements ENABLE ROW LEVEL SECURITY;
ALTER TABLE cash_closings ENABLE ROW LEVEL SECURITY;

-- RLS policies for cash_movements
DROP POLICY IF EXISTS cash_movements_tenant_isolation ON cash_movements;
CREATE POLICY cash_movements_tenant_isolation ON cash_movements
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

-- RLS policies for cash_closings
DROP POLICY IF EXISTS cash_closings_tenant_isolation ON cash_closings;
CREATE POLICY cash_closings_tenant_isolation ON cash_closings
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

-- ============================================================================
-- Triggers
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'cash_movements_updated_at'
    ) THEN
        CREATE TRIGGER cash_movements_updated_at
            BEFORE UPDATE ON cash_movements
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'cash_closings_updated_at'
    ) THEN
        CREATE TRIGGER cash_closings_updated_at
            BEFORE UPDATE ON cash_closings
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END;
$$;
