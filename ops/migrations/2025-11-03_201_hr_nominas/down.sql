-- ============================================================================
-- Migration Rollback: 2025-11-03_201_hr_nominas
-- Description: Rollback of payroll system
-- ============================================================================

-- Drop triggers
DROP TRIGGER IF EXISTS payrolls_updated_at ON payrolls;
DROP TRIGGER IF EXISTS payroll_templates_updated_at ON payroll_templates;

-- Drop functions
DROP FUNCTION IF EXISTS update_updated_at_column();

-- Drop RLS policies
DROP POLICY IF EXISTS tenant_isolation_payrolls ON payrolls;
DROP POLICY IF EXISTS tenant_isolation_payroll_concepts ON payroll_concepts;
DROP POLICY IF EXISTS tenant_isolation_payroll_templates ON payroll_templates;

-- Drop tables (in reverse order of dependencies)
DROP TABLE IF EXISTS payroll_concepts CASCADE;
DROP TABLE IF EXISTS payroll_templates CASCADE;
DROP TABLE IF EXISTS payrolls CASCADE;

-- Drop ENUM types
DROP TYPE IF EXISTS payroll_type CASCADE;
DROP TYPE IF EXISTS payroll_status CASCADE;
