-- Migration: 2026-05-01_001_journal_sequences (rollback)
BEGIN;
DROP INDEX IF EXISTS idx_journal_sequences_tenant;
DROP TABLE IF EXISTS journal_sequences;
COMMIT;
