-- Migration: 2025-11-03_180_hr_empleados
-- Description: Base tables for HR module (employees + vacations)
-- Updated: 2025-11-17 - Spanish to English names

SET row_security = off;

-- Ensure helper trigger function exists (idempotent)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Table: employees
-- ============================================================================
CREATE TABLE IF NOT EXISTS employees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID,
    code VARCHAR(50),
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255),
    document_id VARCHAR(50),
    birth_date DATE,
    hire_date DATE NOT NULL DEFAULT CURRENT_DATE,
    termination_date DATE,
    position VARCHAR(100),
    department VARCHAR(100),
    base_salary NUMERIC(12,2),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_employees_tenant ON employees(tenant_id);
CREATE INDEX IF NOT EXISTS idx_employees_user ON employees(user_id);
CREATE INDEX IF NOT EXISTS idx_employees_is_active ON employees(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_employees_department ON employees(department);

COMMENT ON TABLE employees IS 'Employee records per tenant';
COMMENT ON COLUMN employees.base_salary IS 'Monthly base salary for the employee';

ALTER TABLE employees ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_employees ON employees;
CREATE POLICY tenant_isolation_employees ON employees
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

-- ============================================================================
-- Table: vacations
-- ============================================================================
CREATE TABLE IF NOT EXISTS vacations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    days INTEGER NOT NULL CHECK (days > 0),
    status VARCHAR(20) NOT NULL DEFAULT 'requested',
    approved_by UUID,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vacations_tenant ON vacations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_vacations_employee ON vacations(employee_id);
CREATE INDEX IF NOT EXISTS idx_vacations_status ON vacations(status);

COMMENT ON TABLE vacations IS 'Vacation requests associated with employees';

ALTER TABLE vacations ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_vacations ON vacations;
CREATE POLICY tenant_isolation_vacations ON vacations
    USING (
        EXISTS (
            SELECT 1
            FROM employees e
            WHERE e.id = vacations.employee_id
              AND e.tenant_id::text = current_setting('app.tenant_id', TRUE)
        )
    );

-- ============================================================================
-- Triggers
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'employees_updated_at'
    ) THEN
        CREATE TRIGGER employees_updated_at
            BEFORE UPDATE ON employees
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'vacations_updated_at'
    ) THEN
        CREATE TRIGGER vacations_updated_at
            BEFORE UPDATE ON vacations
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END;
$$;
