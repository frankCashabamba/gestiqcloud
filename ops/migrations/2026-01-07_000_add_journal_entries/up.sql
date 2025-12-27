-- =============================================================================
-- Migration: 2026-01-07_000_add_journal_entries
-- Description: Create a dedicated journal entry schema for accounting + journal lines.
-- =============================================================================
BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_type WHERE typname = 'entry_status'
    ) THEN
        CREATE TYPE entry_status AS ENUM ('DRAFT', 'VALIDATED', 'POSTED', 'CANCELLED');
    END IF;
END$$;

CREATE TABLE IF NOT EXISTS journal_entries (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    number VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    type VARCHAR(50) NOT NULL DEFAULT 'OPERATIONS',
    description TEXT NOT NULL,
    debit_total NUMERIC(14, 2) NOT NULL DEFAULT 0,
    credit_total NUMERIC(14, 2) NOT NULL DEFAULT 0,
    is_balanced BOOLEAN NOT NULL DEFAULT FALSE,
    status entry_status NOT NULL DEFAULT 'DRAFT',
    ref_doc_type VARCHAR(50),
    ref_doc_id UUID,
    created_by UUID,
    posted_by UUID,
    posted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id)
);

ALTER TABLE journal_entries
    ADD CONSTRAINT uq_journal_entries_number UNIQUE (number);

CREATE INDEX IF NOT EXISTS ix_journal_entries_tenant_id
    ON journal_entries(tenant_id);
CREATE INDEX IF NOT EXISTS ix_journal_entries_status
    ON journal_entries(status);
CREATE INDEX IF NOT EXISTS ix_journal_entries_date
    ON journal_entries(date);

CREATE TABLE IF NOT EXISTS journal_entry_lines (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    entry_id UUID NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
    account_id UUID NOT NULL REFERENCES chart_of_accounts(id) ON DELETE RESTRICT,
    debit NUMERIC(14, 2) NOT NULL DEFAULT 0,
    credit NUMERIC(14, 2) NOT NULL DEFAULT 0,
    description VARCHAR(255),
    line_number INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_journal_entry_lines_entry_id
    ON journal_entry_lines(entry_id);
CREATE INDEX IF NOT EXISTS ix_journal_entry_lines_account_id
    ON journal_entry_lines(account_id);

COMMIT;
