# Módulo: registry

Propósito: registro de empresas/tenants y asignación inicial de módulos.

## Endpoints
- Tenant: `interface/http/tenant.py` prefix `/modules`.
- Admin: `interface/http/admin.py` prefix `/modules` (montado bajo `/api/v1/admin`).

## Componentes clave
- `service.py`: lógica de registro.
- `models.py`: entidades de registro.
- `interface/http` para exposición.

## Notas
- Interactúa con `modulos` y `settings` para inicializar configuración por tenant.
