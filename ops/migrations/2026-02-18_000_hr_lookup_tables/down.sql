-- Rollback: 2026-02-18_000_hr_lookup_tables

BEGIN;

DROP TABLE IF EXISTS gender_types CASCADE;
DROP TABLE IF EXISTS deduction_types CASCADE;
DROP TABLE IF EXISTS contract_types CASCADE;
DROP TABLE IF EXISTS employee_statuses CASCADE;

COMMIT;
