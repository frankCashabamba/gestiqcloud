# Módulo Quotes

Estado: Activo
Madurez: 3/5
Owner: Frontend/Backend
Riesgo: Medio

## Implementado

- Listado, formulario, detalle, aprobación, conversión y eliminación de presupuestos.

## Parcial

- Frontend usa permisos CRUD esperados; backend puede usar `quotes.manage`.
- Conversión depende del documento/venta backend.

## Pendiente

- Alinear permisos granulares.
- E2E quote -> approve -> convert.

## Endpoints usados

- `/api/v1/tenant/quotes/*`

## Permisos

- `quotes:read`
- `quotes:create`
- `quotes:update`
- `quotes:delete`
- `quotes:manage`

## Tests mínimos

- Crear presupuesto.
- Aprobar presupuesto.
- Convertir a venta.
- Bloquear acciones sin permiso.
