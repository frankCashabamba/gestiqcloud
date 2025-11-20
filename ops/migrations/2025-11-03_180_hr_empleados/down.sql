-- Down migration for 2025-11-03_180_hr_empleados

DROP POLICY IF EXISTS tenant_isolation_vacations ON vacations;
DROP POLICY IF EXISTS tenant_isolation_employees ON employees;

DROP TABLE IF EXISTS vacations;
DROP TABLE IF EXISTS employees;
