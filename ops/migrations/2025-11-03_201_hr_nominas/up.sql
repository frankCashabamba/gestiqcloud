-- ============================================================================
-- Migration: 2025-11-03_201_hr_nominas
-- Description: Complete payroll system with earnings, deductions and concepts
-- Updated: 2025-11-17 - Spanish to English names
-- ============================================================================

-- Create ENUM types for payroll
DO $$ BEGIN
  CREATE TYPE payroll_status AS ENUM ('DRAFT', 'APPROVED', 'PAID', 'CANCELLED');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE payroll_type AS ENUM ('MONTHLY', 'EXTRA', 'SEVERANCE', 'SPECIAL');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

COMMENT ON TYPE payroll_status IS 'Payroll status: DRAFT=Draft, APPROVED=Approved, PAID=Paid, CANCELLED=Cancelled';
COMMENT ON TYPE payroll_type IS 'Payroll types: MONTHLY=Regular, EXTRA=Extra pay, SEVERANCE=Severance, SPECIAL=Special payments';

-- ============================================================================
-- Table: payrolls
-- ============================================================================

CREATE TABLE IF NOT EXISTS payrolls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Numbering and references
    number VARCHAR(50) NOT NULL UNIQUE,
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE RESTRICT,

    -- Period
    period_month INTEGER NOT NULL CHECK (period_month >= 1 AND period_month <= 12),
    period_year INTEGER NOT NULL CHECK (period_year >= 2020 AND period_year <= 2100),
    type payroll_type NOT NULL DEFAULT 'MONTHLY',

    -- === EARNINGS (positive) ===
    base_salary NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (base_salary >= 0),
    allowances NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (allowances >= 0),
    overtime NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (overtime >= 0),
    other_earnings NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (other_earnings >= 0),
    total_earnings NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (total_earnings >= 0),

    -- === DEDUCTIONS (negative) ===
    social_security NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (social_security >= 0),
    income_tax NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (income_tax >= 0),
    other_deductions NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (other_deductions >= 0),
    total_deductions NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (total_deductions >= 0),

    -- === TOTALS ===
    net_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,

    -- === PAYMENT ===
    payment_date DATE,
    payment_method VARCHAR(50),

    -- === STATUS ===
    status payroll_status NOT NULL DEFAULT 'DRAFT',

    -- === ADDITIONAL INFO ===
    notes TEXT,
    concepts_json JSONB,

    -- === AUDIT ===
    approved_by UUID,
    approved_at TIMESTAMPTZ,
    created_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- === CONSTRAINTS ===
    CONSTRAINT payrolls_period_employee_type_unique
        UNIQUE (tenant_id, employee_id, period_month, period_year, type)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_payrolls_tenant_id ON payrolls(tenant_id);
CREATE INDEX IF NOT EXISTS idx_payrolls_employee_id ON payrolls(employee_id);
CREATE INDEX IF NOT EXISTS idx_payrolls_period ON payrolls(period_year, period_month);
CREATE INDEX IF NOT EXISTS idx_payrolls_status ON payrolls(status);
CREATE INDEX IF NOT EXISTS idx_payrolls_number ON payrolls(number);
CREATE INDEX IF NOT EXISTS idx_payrolls_payment_date ON payrolls(payment_date) WHERE payment_date IS NOT NULL;

-- Comments
COMMENT ON TABLE payrolls IS 'Monthly payrolls for employees with earnings, deductions and totals';
COMMENT ON COLUMN payrolls.number IS 'Unique payroll number (PAY-YYYY-MM-NNNN)';
COMMENT ON COLUMN payrolls.base_salary IS 'Base salary for the period';
COMMENT ON COLUMN payrolls.allowances IS 'Sum of salary allowances (transport, night work, etc.)';
COMMENT ON COLUMN payrolls.overtime IS 'Payment for overtime hours';
COMMENT ON COLUMN payrolls.other_earnings IS 'Other earnings';
COMMENT ON COLUMN payrolls.total_earnings IS 'Total earnings (sum of earnings)';
COMMENT ON COLUMN payrolls.social_security IS 'Social security contribution';
COMMENT ON COLUMN payrolls.income_tax IS 'Income tax withholding';
COMMENT ON COLUMN payrolls.other_deductions IS 'Other deductions (advances, garnishments, etc.)';
COMMENT ON COLUMN payrolls.total_deductions IS 'Total deductions (sum of deductions)';
COMMENT ON COLUMN payrolls.net_amount IS 'Net amount to pay (earnings - deductions)';
COMMENT ON COLUMN payrolls.concepts_json IS 'Breakdown of concepts in JSON format';

-- ============================================================================
-- Table: payroll_concepts
-- ============================================================================

CREATE TABLE IF NOT EXISTS payroll_concepts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payroll_id UUID NOT NULL REFERENCES payrolls(id) ON DELETE CASCADE,

    -- Concept type
    type VARCHAR(20) NOT NULL CHECK (type IN ('EARNING', 'DEDUCTION')),
    code VARCHAR(50) NOT NULL,
    description VARCHAR(255) NOT NULL,

    -- Amount
    amount NUMERIC(12, 2) NOT NULL CHECK (amount >= 0),

    -- Configuration
    is_base BOOLEAN NOT NULL DEFAULT TRUE,

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_payroll_concepts_payroll_id ON payroll_concepts(payroll_id);
CREATE INDEX IF NOT EXISTS idx_payroll_concepts_type ON payroll_concepts(type);
CREATE INDEX IF NOT EXISTS idx_payroll_concepts_code ON payroll_concepts(code);

-- Comments
COMMENT ON TABLE payroll_concepts IS 'Individual payroll concepts (earnings and deductions)';
COMMENT ON COLUMN payroll_concepts.type IS 'EARNING (positive) or DEDUCTION (negative)';
COMMENT ON COLUMN payroll_concepts.code IS 'Concept code (e.g., TRANSPORT_BONUS, ADVANCE)';
COMMENT ON COLUMN payroll_concepts.amount IS 'Concept amount (always positive)';
COMMENT ON COLUMN payroll_concepts.is_base IS 'Whether it counts for contribution base';

-- ============================================================================
-- Table: payroll_templates
-- ============================================================================

CREATE TABLE IF NOT EXISTS payroll_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,

    -- Configuration
    name VARCHAR(100) NOT NULL,
    description TEXT,
    concepts_json JSONB NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT payroll_templates_tenant_employee_name_unique
        UNIQUE (tenant_id, employee_id, name)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_payroll_templates_tenant_id ON payroll_templates(tenant_id);
CREATE INDEX IF NOT EXISTS idx_payroll_templates_employee_id ON payroll_templates(employee_id);
CREATE INDEX IF NOT EXISTS idx_payroll_templates_is_active ON payroll_templates(is_active) WHERE is_active = TRUE;

-- Comments
COMMENT ON TABLE payroll_templates IS 'Payroll templates per employee to generate payrolls quickly';
COMMENT ON COLUMN payroll_templates.concepts_json IS 'Template concepts in JSON format (can be customized)';

-- ============================================================================
-- Triggers
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'payrolls_updated_at'
    ) THEN
        CREATE TRIGGER payrolls_updated_at
            BEFORE UPDATE ON payrolls
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'payroll_templates_updated_at'
    ) THEN
        CREATE TRIGGER payroll_templates_updated_at
            BEFORE UPDATE ON payroll_templates
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END;
$$;

-- Enable RLS
ALTER TABLE payrolls ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_payrolls ON payrolls;
CREATE POLICY tenant_isolation_payrolls ON payrolls
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

ALTER TABLE payroll_concepts ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_payroll_concepts ON payroll_concepts;
CREATE POLICY tenant_isolation_payroll_concepts ON payroll_concepts
    USING (
        EXISTS (
            SELECT 1 FROM payrolls p
            WHERE p.id = payroll_concepts.payroll_id
              AND p.tenant_id::text = current_setting('app.tenant_id', TRUE)
        )
    );

ALTER TABLE payroll_templates ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_payroll_templates ON payroll_templates;
CREATE POLICY tenant_isolation_payroll_templates ON payroll_templates
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));
