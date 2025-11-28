# Módulo: company

Propósito: entidades de empresa/tenant y configuración base.

## Endpoints
- Tenant: `interface/http/tenant.py` prefix `/company`.
- Admin: `interface/http/admin.py` prefix `/admin/companies` (montado bajo `/api/v1`).

## Componentes clave
- Modelos y servicios para datos de empresa.

## Notas
- Se relaciona con `registry`, `settings` y `modulos` para configuración inicial.
