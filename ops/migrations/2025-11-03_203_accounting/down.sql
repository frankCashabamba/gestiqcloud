-- ============================================================================
-- Migration Rollback: 2025-11-03_203_accounting
-- Description: Rollback of accounting system
-- ============================================================================

-- Drop triggers
DROP TRIGGER IF EXISTS chart_of_accounts_updated_at ON chart_of_accounts;
DROP TRIGGER IF EXISTS journal_entries_updated_at ON journal_entries;

-- Drop RLS policies
DROP POLICY IF EXISTS tenant_isolation_chart_of_accounts ON chart_of_accounts;
DROP POLICY IF EXISTS tenant_isolation_journal_entries ON journal_entries;
DROP POLICY IF EXISTS tenant_isolation_journal_entry_lines ON journal_entry_lines;

-- Drop tables (in reverse order of dependencies)
DROP TABLE IF EXISTS journal_entry_lines CASCADE;
DROP TABLE IF EXISTS journal_entries CASCADE;
DROP TABLE IF EXISTS chart_of_accounts CASCADE;

-- Drop ENUM types
DROP TYPE IF EXISTS account_type CASCADE;
DROP TYPE IF EXISTS journal_entry_status CASCADE;

-- Drop functions
DROP FUNCTION IF EXISTS update_updated_at_column();
