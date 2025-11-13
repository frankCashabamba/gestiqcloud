# 2025-11-03_180_hr_empleados

Crea las tablas base `empleados` y `vacaciones` del módulo de RRHH, incluyendo índices y políticas RLS. Es requisito previo para `2025-11-03_201_hr_nominas`, que referencia `empleados`.

## Deploy notes

1. Ejecuta `scripts/init.ps1 local` o el runner habitual para aplicar la migración antes de las nóminas.
2. No requiere data migration: las tablas se crean vacías y se poblarán vía API.

## Rollback plan

Ejecutar `down.sql` (se eliminarán las tablas y políticas, por lo que se perderán solicitudes de vacaciones y empleados registrados).
