-- Rollback: 2026-02-14_002_profit_snapshots

BEGIN;

DROP TABLE IF EXISTS product_profit_snapshots;
DROP TABLE IF EXISTS profit_snapshots_daily;

COMMIT;
