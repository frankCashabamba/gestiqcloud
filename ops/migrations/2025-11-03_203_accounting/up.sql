-- ============================================================================
-- Migration: 2025-11-03_203_accounting
-- Description: Complete accounting system (Chart of Accounts + Journal Entries)
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

-- Create ENUM types for accounting
DO $$ BEGIN
  CREATE TYPE account_type AS ENUM ('ASSET', 'LIABILITY', 'EQUITY', 'INCOME', 'EXPENSE');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE journal_entry_status AS ENUM ('DRAFT', 'VALIDATED', 'POSTED', 'CANCELLED');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

COMMENT ON TYPE account_type IS 'Account type: ASSET, LIABILITY, EQUITY, INCOME, EXPENSE';
COMMENT ON TYPE journal_entry_status IS 'Journal entry status: DRAFT=Unvalidated, VALIDATED=Balanced, POSTED=Posted, CANCELLED=Cancelled';

-- ============================================================================
-- Table: chart_of_accounts
-- ============================================================================

CREATE TABLE IF NOT EXISTS chart_of_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Code and name
    code VARCHAR(20) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Classification
    type account_type NOT NULL,
    level INTEGER NOT NULL CHECK (level >= 1 AND level <= 4),

    -- Hierarchy
    parent_id UUID REFERENCES chart_of_accounts(id) ON DELETE CASCADE,

    -- Configuration
    is_postable BOOLEAN NOT NULL DEFAULT TRUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    -- Balances (calculated)
    debit_balance NUMERIC(14, 2) NOT NULL DEFAULT 0,
    credit_balance NUMERIC(14, 2) NOT NULL DEFAULT 0,
    balance NUMERIC(14, 2) NOT NULL DEFAULT 0,

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- === CONSTRAINTS ===
    CONSTRAINT chart_of_accounts_tenant_code_unique UNIQUE (tenant_id, code)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_chart_of_accounts_tenant_id ON chart_of_accounts(tenant_id);
CREATE INDEX IF NOT EXISTS idx_chart_of_accounts_code ON chart_of_accounts(code);
CREATE INDEX IF NOT EXISTS idx_chart_of_accounts_type ON chart_of_accounts(type);
CREATE INDEX IF NOT EXISTS idx_chart_of_accounts_parent_id ON chart_of_accounts(parent_id) WHERE parent_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_chart_of_accounts_is_active ON chart_of_accounts(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_chart_of_accounts_is_postable ON chart_of_accounts(is_postable) WHERE is_postable = TRUE;

-- Comments
COMMENT ON TABLE chart_of_accounts IS 'Hierarchical chart of accounts';
COMMENT ON COLUMN chart_of_accounts.code IS 'Account code (e.g., 5700001)';
COMMENT ON COLUMN chart_of_accounts.type IS 'ASSET, LIABILITY, EQUITY, INCOME, EXPENSE';
COMMENT ON COLUMN chart_of_accounts.level IS 'Hierarchical level (1=Group, 2=Subgroup, 3=Account, 4=Subaccount)';
COMMENT ON COLUMN chart_of_accounts.parent_id IS 'ID of parent account (NULL if level 1)';
COMMENT ON COLUMN chart_of_accounts.is_postable IS 'Whether it allows direct postings (TRUE for subaccounts)';
COMMENT ON COLUMN chart_of_accounts.debit_balance IS 'Accumulated debit balance';
COMMENT ON COLUMN chart_of_accounts.credit_balance IS 'Accumulated credit balance';
COMMENT ON COLUMN chart_of_accounts.balance IS 'Net balance (debit - credit)';

-- ============================================================================
-- Table: journal_entries
-- ============================================================================

CREATE TABLE IF NOT EXISTS journal_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Numbering
    number VARCHAR(50) NOT NULL UNIQUE,

    -- Date and type
    date DATE NOT NULL,
    type VARCHAR(50) NOT NULL DEFAULT 'OPERATIONS',

    -- Description
    description TEXT NOT NULL,

    -- Totals
    debit_total NUMERIC(14, 2) NOT NULL DEFAULT 0,
    credit_total NUMERIC(14, 2) NOT NULL DEFAULT 0,
    is_balanced BOOLEAN NOT NULL DEFAULT FALSE,

    -- Status
    status journal_entry_status NOT NULL DEFAULT 'DRAFT',

    -- Reference to source document
    ref_doc_type VARCHAR(50),
    ref_doc_id UUID,

    -- Audit
    created_by UUID,
    posted_by UUID,
    posted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_journal_entries_tenant_id ON journal_entries(tenant_id);
CREATE INDEX IF NOT EXISTS idx_journal_entries_number ON journal_entries(number);
CREATE INDEX IF NOT EXISTS idx_journal_entries_date ON journal_entries(date);
CREATE INDEX IF NOT EXISTS idx_journal_entries_status ON journal_entries(status);
CREATE INDEX IF NOT EXISTS idx_journal_entries_type ON journal_entries(type);
CREATE INDEX IF NOT EXISTS idx_journal_entries_ref_doc ON journal_entries(ref_doc_type, ref_doc_id) WHERE ref_doc_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_journal_entries_date_tenant ON journal_entries(date, tenant_id);

-- Comments
COMMENT ON TABLE journal_entries IS 'Journal entries (book of accounts)';
COMMENT ON COLUMN journal_entries.number IS 'Unique number (JNL-YYYY-NNNN)';
COMMENT ON COLUMN journal_entries.type IS 'OPENING, OPERATIONS, REGULARIZATION, CLOSING';
COMMENT ON COLUMN journal_entries.debit_total IS 'Total sum of debits';
COMMENT ON COLUMN journal_entries.credit_total IS 'Total sum of credits';
COMMENT ON COLUMN journal_entries.is_balanced IS 'True if debit = credit';
COMMENT ON COLUMN journal_entries.status IS 'Status of the journal entry';
COMMENT ON COLUMN journal_entries.ref_doc_type IS 'Type of source document (invoice, payment, etc.)';

-- ============================================================================
-- Table: journal_entry_lines
-- ============================================================================

CREATE TABLE IF NOT EXISTS journal_entry_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Reference to journal entry
    journal_entry_id UUID NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,

    -- Reference to account
    account_id UUID NOT NULL REFERENCES chart_of_accounts(id) ON DELETE RESTRICT,

    -- Amount
    debit NUMERIC(14, 2) DEFAULT 0,
    credit NUMERIC(14, 2) DEFAULT 0,

    -- Description
    description VARCHAR(500),

    -- Analytics (optional)
    cost_center VARCHAR(50),
    project_code VARCHAR(50),

    -- Order in entry
    line_number INTEGER NOT NULL,

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_journal_entry_lines_entry_id ON journal_entry_lines(journal_entry_id);
CREATE INDEX IF NOT EXISTS idx_journal_entry_lines_account_id ON journal_entry_lines(account_id);
CREATE INDEX IF NOT EXISTS idx_journal_entry_lines_line_number ON journal_entry_lines(journal_entry_id, line_number);

-- Comments
COMMENT ON TABLE journal_entry_lines IS 'Lines of journal entries (individual debit/credit postings)';
COMMENT ON COLUMN journal_entry_lines.debit IS 'Debit amount (positive) or NULL';
COMMENT ON COLUMN journal_entry_lines.credit IS 'Credit amount (positive) or NULL';
COMMENT ON COLUMN journal_entry_lines.cost_center IS 'Optional cost center for analytics';
COMMENT ON COLUMN journal_entry_lines.project_code IS 'Optional project code for analytics';

-- ============================================================================
-- RLS (Row Level Security)
-- ============================================================================

ALTER TABLE chart_of_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE journal_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE journal_entry_lines ENABLE ROW LEVEL SECURITY;

-- RLS policies for chart_of_accounts
DROP POLICY IF EXISTS tenant_isolation_chart_of_accounts ON chart_of_accounts;
CREATE POLICY tenant_isolation_chart_of_accounts ON chart_of_accounts
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

-- RLS policies for journal_entries
DROP POLICY IF EXISTS tenant_isolation_journal_entries ON journal_entries;
CREATE POLICY tenant_isolation_journal_entries ON journal_entries
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

-- RLS policies for journal_entry_lines
DROP POLICY IF EXISTS tenant_isolation_journal_entry_lines ON journal_entry_lines;
CREATE POLICY tenant_isolation_journal_entry_lines ON journal_entry_lines
    USING (
        EXISTS (
            SELECT 1 FROM journal_entries je
            WHERE je.id = journal_entry_lines.journal_entry_id
              AND je.tenant_id::text = current_setting('app.tenant_id', TRUE)
        )
    );

-- ============================================================================
-- Triggers
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'chart_of_accounts_updated_at'
    ) THEN
        CREATE TRIGGER chart_of_accounts_updated_at
            BEFORE UPDATE ON chart_of_accounts
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'journal_entries_updated_at'
    ) THEN
        CREATE TRIGGER journal_entries_updated_at
            BEFORE UPDATE ON journal_entries
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END;
$$;
