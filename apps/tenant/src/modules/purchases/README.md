# Módulo Purchases

Estado: Activo
Madurez: 3/5
Owner: Frontend/Backend
Riesgo: Medio

## Implementado

- Listado, formulario, detalle y recepción de compras.
- Integración con producción cuando aplica.

## Parcial

- Recepción e inventario requieren validación end-to-end.

## Pendiente

- E2E compra -> recepción -> stock.
- Validar costes y proveedores reales.

## Endpoints usados

- `/api/v1/tenant/purchases/*`

## Permisos

- `purchases:read`
- `purchases:create`
- `purchases:update`
- `purchases:delete`

## Tests mínimos

- Crear compra.
- Editar compra.
- Recibir compra.
- Ver detalle de producción.
