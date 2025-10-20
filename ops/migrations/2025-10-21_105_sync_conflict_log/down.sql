-- Reverse migration: Drop sync conflict log table

-- Drop RLS policy
DROP POLICY IF EXISTS tenant_isolation ON sync_conflict_log;

-- Disable RLS
ALTER TABLE sync_conflict_log DISABLE ROW LEVEL SECURITY;

-- Drop table
DROP TABLE IF EXISTS sync_conflict_log;
