-- ============================================================================
-- Migration: 2025-11-18_330_expenses_system
-- Description: Expense tracking and management
-- ============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create ENUM types
DO $$ BEGIN
  CREATE TYPE expense_status AS ENUM ('DRAFT', 'SUBMITTED', 'APPROVED', 'REJECTED', 'PAID');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ============================================================================
-- Table: expenses
-- ============================================================================

CREATE TABLE IF NOT EXISTS expenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Reference
    number VARCHAR(50) NOT NULL UNIQUE,

    -- Employee/Department
    employee_id UUID REFERENCES employees(id) ON DELETE SET NULL,
    department VARCHAR(100),

    -- Expense details
    concept VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    subcategory VARCHAR(100),

    -- Amounts
    amount NUMERIC(12, 2) NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'EUR',
    vat NUMERIC(12, 2) DEFAULT 0,
    total NUMERIC(12, 2) NOT NULL,

    -- Date
    expense_date DATE NOT NULL,

    -- Payment
    payment_method VARCHAR(50),
    invoice_number VARCHAR(50),

    -- Status
    status expense_status NOT NULL DEFAULT 'DRAFT',

    -- Notes
    notes TEXT,

    -- Audit
    created_by UUID,
    approved_by UUID,
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_expenses_tenant ON expenses(tenant_id);
CREATE INDEX IF NOT EXISTS idx_expenses_number ON expenses(number);
CREATE INDEX IF NOT EXISTS idx_expenses_employee ON expenses(employee_id);
CREATE INDEX IF NOT EXISTS idx_expenses_status ON expenses(status);
CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(expense_date);
CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category);

COMMENT ON TABLE expenses IS 'Employee and operational expenses';
COMMENT ON COLUMN expenses.concept IS 'Expense concept/description';
COMMENT ON COLUMN expenses.payment_method IS 'How it was paid (cash, card, bank transfer, etc.)';
COMMENT ON COLUMN expenses.invoice_number IS 'Invoice/receipt number if applicable';

ALTER TABLE expenses ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_expenses ON expenses;
CREATE POLICY tenant_isolation_expenses ON expenses
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

-- ============================================================================
-- Triggers
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'expenses_updated_at'
    ) THEN
        CREATE TRIGGER expenses_updated_at
            BEFORE UPDATE ON expenses
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END;
$$;

COMMIT;
