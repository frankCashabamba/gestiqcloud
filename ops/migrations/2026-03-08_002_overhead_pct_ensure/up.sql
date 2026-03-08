-- Migración correctiva: garantiza que overhead_pct existe en recipes
-- La migración 2026-03-08_001 pudo quedar registrada en _migrations sin
-- aplicarse realmente. Esta migración usa IF NOT EXISTS para ser idempotente.
ALTER TABLE recipes
    ADD COLUMN IF NOT EXISTS overhead_pct NUMERIC(5, 2) DEFAULT 5;
