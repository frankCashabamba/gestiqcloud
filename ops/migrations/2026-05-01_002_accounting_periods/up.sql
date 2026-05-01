-- Migration: 2026-05-01_002_accounting_periods
-- Períodos contables mensuales por tenant para cierre/apertura/regularización.
BEGIN;

CREATE TABLE IF NOT EXISTS accounting_periods (
    id          UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID    NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    year        INTEGER NOT NULL,
    month       INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    quarter     INTEGER NULL CHECK (quarter IS NULL OR quarter BETWEEN 1 AND 4),
    status      VARCHAR(16) NOT NULL DEFAULT 'OPEN'
                CHECK (status IN ('OPEN','CLOSED')),
    closed_at   TIMESTAMPTZ NULL,
    closed_by   UUID NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_accounting_periods_tenant_ym UNIQUE (tenant_id, year, month)
);

CREATE INDEX IF NOT EXISTS idx_accounting_periods_tenant_year
    ON accounting_periods(tenant_id, year);
CREATE INDEX IF NOT EXISTS idx_accounting_periods_status
    ON accounting_periods(tenant_id, status);

COMMIT;
