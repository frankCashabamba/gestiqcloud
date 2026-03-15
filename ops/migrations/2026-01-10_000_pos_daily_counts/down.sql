BEGIN;

DROP INDEX IF EXISTS ix_pos_daily_counts_shift_id;
DROP INDEX IF EXISTS ix_pos_daily_counts_register_id;
DROP INDEX IF EXISTS ix_pos_daily_counts_tenant_id;
DROP TABLE IF EXISTS pos_daily_counts;

COMMIT;
