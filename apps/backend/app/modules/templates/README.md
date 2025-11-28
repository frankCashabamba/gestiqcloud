# Módulo: templates

Propósito: gestión de plantillas (email/UI/pdf) por tenant/sector.

## Endpoints
- Tenant: `interface/http/tenant.py` prefix `/templates`.
- Admin: `interface/http/admin.py` prefix `/admin/templates` (montado bajo `/api/v1`).

## Componentes clave
- `services.py`: lógica de plantillas.
- `application`/`infrastructure` según implementación.
- Plantillas físicas en `app/templates/` y `app/templates/pdf/`.

## Notas
- Usado por invoicing/einvoicing y notificaciones.
