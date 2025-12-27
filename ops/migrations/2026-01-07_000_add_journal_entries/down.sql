-- =============================================================================
-- Migration: 2026-01-07_000_add_journal_entries
-- Description: Revert the accounting journal entry schema.
-- =============================================================================
BEGIN;

DROP TABLE IF EXISTS journal_entry_lines;
DROP TABLE IF EXISTS journal_entries;
DROP TYPE IF EXISTS entry_status;

COMMIT;
