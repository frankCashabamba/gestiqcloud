-- Down migration: drop tables created in 2025-11-27_000_create_missing_tables

BEGIN;

DROP TABLE IF EXISTS chart_of_accounts CASCADE;
DROP TABLE IF EXISTS import_batches CASCADE;
DROP TABLE IF EXISTS tenant_field_configs CASCADE;

COMMIT;
