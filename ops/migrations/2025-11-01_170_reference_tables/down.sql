-- Revertir tablas de referencia
-- Migration rollback: 2025-11-01_170_reference_tables

BEGIN;

DROP TABLE IF EXISTS tenant_field_configs CASCADE;
DROP TABLE IF EXISTS timezones CASCADE;
DROP TABLE IF EXISTS locales CASCADE;
DROP TABLE IF EXISTS countries CASCADE;
DROP TABLE IF EXISTS currencies CASCADE;

COMMIT;
