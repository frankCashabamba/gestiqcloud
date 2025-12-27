-- Migration: 2026-01-10_000_pos_daily_counts
-- Description: Guardar reportes diarios de turno para el módulo POS.

BEGIN;

CREATE TABLE IF NOT EXISTS pos_daily_counts (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    register_id UUID NOT NULL REFERENCES pos_registers(id) ON DELETE CASCADE,
    shift_id UUID NOT NULL REFERENCES pos_shifts(id) ON DELETE CASCADE,
    count_date DATE NOT NULL,
    opening_float NUMERIC(14,2) NOT NULL DEFAULT 0,
    cash_sales NUMERIC(14,2) NOT NULL DEFAULT 0,
    card_sales NUMERIC(14,2) NOT NULL DEFAULT 0,
    other_sales NUMERIC(14,2) NOT NULL DEFAULT 0,
    total_sales NUMERIC(14,2) NOT NULL DEFAULT 0,
    expected_cash NUMERIC(14,2) NOT NULL DEFAULT 0,
    counted_cash NUMERIC(14,2) NOT NULL DEFAULT 0,
    discrepancy NUMERIC(14,2) NOT NULL DEFAULT 0,
    loss_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
    loss_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id),
    CONSTRAINT uq_pos_daily_counts_shift UNIQUE (shift_id)
);

CREATE INDEX IF NOT EXISTS ix_pos_daily_counts_tenant_id
    ON pos_daily_counts(tenant_id);
CREATE INDEX IF NOT EXISTS ix_pos_daily_counts_register_id
    ON pos_daily_counts(register_id);
CREATE INDEX IF NOT EXISTS ix_pos_daily_counts_shift_id
    ON pos_daily_counts(shift_id);

COMMIT;
