-- Down migration for 2025-11-03_180_hr_empleados

DROP POLICY IF EXISTS tenant_isolation_vacaciones ON vacaciones;
DROP POLICY IF EXISTS tenant_isolation_empleados ON empleados;

DROP TABLE IF EXISTS vacaciones;
DROP TABLE IF EXISTS empleados;
