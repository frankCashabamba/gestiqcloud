# Módulo Templates

Estado: Parcial
Madurez: 2/5
Owner: Frontend/Backend
Riesgo: Medio

## Implementado

- Visor de configuración UI/templates.
- Ruta protegida por `templates:manage`.

## Parcial

- Actualmente funciona como visor/configuración técnica.
- Backend usa scope tenant/admin; granularidad de permisos debe alinearse.

## Pendiente

- Separar lectura (`templates:read`) y edición (`templates:manage`) si se agregan formularios.
- E2E acceso permitido/denegado.

## Endpoints usados

- `/api/v1/tenant/templates/*`
- `/api/v1/admin/templates/*`

## Permisos

- `templates:read`
- `templates:manage`

## Tests mínimos

- Abrir visor.
- Refrescar configuración.
- Bloquear acceso sin permiso.
