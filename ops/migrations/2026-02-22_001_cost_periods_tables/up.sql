-- Migration: 2026-02-22_001_cost_periods_tables
-- Description: Create cost_periods and cost_period_validations tables for monthly indirect cost tracking.

BEGIN;

CREATE TABLE IF NOT EXISTS cost_periods (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID            NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    month           VARCHAR(7)      NOT NULL,
    labor_hour_rate     NUMERIC(12,4) NOT NULL DEFAULT 0,
    labor_paid_hours    NUMERIC(12,4) NOT NULL DEFAULT 160,
    touch_hours_total   NUMERIC(12,4) NULL,
    labor_burden_factor NUMERIC(8,4)  DEFAULT 1.0,
    electricity_cost    NUMERIC(12,4) NOT NULL DEFAULT 0,
    electricity_per_hour NUMERIC(12,4) DEFAULT 0,
    diesel_cost_month   NUMERIC(12,4) NOT NULL DEFAULT 0,
    oven_hours_total    NUMERIC(12,4) NOT NULL DEFAULT 160,
    diesel_per_oven_hour NUMERIC(12,4) DEFAULT 0,
    production_share_pct NUMERIC(5,2) NULL,
    notes           VARCHAR(500)    NULL,
    is_active       BOOLEAN         DEFAULT TRUE,
    created_at      TIMESTAMPTZ     DEFAULT now(),
    updated_at      TIMESTAMPTZ     DEFAULT now(),
    closed_at       TIMESTAMPTZ     NULL,
    UNIQUE (tenant_id, month)
);

CREATE INDEX IF NOT EXISTS idx_cost_periods_tenant_month ON cost_periods (tenant_id, month);
CREATE INDEX IF NOT EXISTS idx_cost_periods_is_active    ON cost_periods (is_active);

CREATE TABLE IF NOT EXISTS cost_period_validations (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    period_id       UUID            NOT NULL,
    validation_type VARCHAR(50)     NOT NULL,
    severity        VARCHAR(20)     NOT NULL DEFAULT 'warning',
    message         VARCHAR(500)    NOT NULL,
    suggested_action VARCHAR(500)   NULL,
    is_resolved     BOOLEAN         DEFAULT FALSE,
    created_at      TIMESTAMPTZ     DEFAULT now(),
    resolved_at     TIMESTAMPTZ     NULL
);

CREATE INDEX IF NOT EXISTS idx_cost_period_validations_period ON cost_period_validations (period_id);

COMMIT;
