-- Migration: 2026-05-01_001_journal_sequences
-- Tabla auxiliar para numeración concurrente segura de asientos contables
-- (combinada con pg_advisory_xact_lock por (tenant_id, year)).
BEGIN;

CREATE TABLE IF NOT EXISTS journal_sequences (
    tenant_id   UUID    NOT NULL,
    year        INTEGER NOT NULL,
    last_number INTEGER NOT NULL DEFAULT 0,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, year)
);

CREATE INDEX IF NOT EXISTS idx_journal_sequences_tenant
    ON journal_sequences(tenant_id);

COMMIT;
