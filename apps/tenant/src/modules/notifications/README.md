# Módulo Notifications

Estado: Parcial
Madurez: 2/5
Owner: Frontend/Backend
Riesgo: Medio

## Implementado

- Centro de notificaciones.
- Acciones de marcar como leída y archivar.
- Ruta protegida por `notifications:read`.

## Parcial

- Backend observado usa tenant/auth, pero no permiso granular para todas las acciones.
- Templates de notificación requieren revisión operativa.

## Pendiente

- Alinear permisos backend con `notifications:read/manage`.
- E2E acceso permitido/denegado.

## Endpoints usados

- `/api/v1/tenant/notifications/*`

## Permisos

- `notifications:read`
- `notifications:manage`

## Tests mínimos

- Ver notificaciones.
- Marcar como leídas.
- Archivar.
- Bloquear acceso sin permiso.
