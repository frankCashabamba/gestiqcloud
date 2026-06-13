# Módulo Webhooks

Estado: Parcial
Madurez: 3/5
Owner: Frontend/Backend
Riesgo: Alto

## Implementado

- Listado y creación de suscripciones.
- Test y eliminación de webhooks.
- Ruta protegida por `webhooks:manage`.

## Parcial

- Frontend usa `webhooks:manage`; roles/locales conservan también `webhooks:read/write`.
- Backend observado requiere tenant scope; revisar granularidad.

## Pendiente

- Métricas visibles de delivery.
- E2E create/test/delete con permisos.

## Endpoints usados

- `/api/v1/tenant/webhooks/*`

## Permisos

- `webhooks:read`
- `webhooks:manage`

## Tests mínimos

- Crear webhook.
- Enviar test.
- Eliminar webhook.
- Bloquear acceso sin permiso.
