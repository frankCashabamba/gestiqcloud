# Módulo Restaurant

Estado: Beta
Madurez: 2/5
Owner: Frontend/Backend
Riesgo: Alto

## Implementado

- Mesas, órdenes y vista de pedido.
- KDS básico cuando está habilitado.

## Parcial

- Integración POS/facturación/impuestos requiere cierre.
- Manifest puede estar deshabilitado según tenant/sector.

## Pendiente

- Smoke restaurante -> pedido -> cierre -> POS/factura.
- Validar permisos KDS.

## Endpoints usados

- `/api/v1/tenant/restaurant/*`

## Permisos

- `restaurant:read`
- `restaurant:manage`
- `restaurant.kds.view`
- `restaurant.kds.manage`

## Tests mínimos

- Abrir mesas.
- Crear pedido.
- Cambiar estado en KDS.
- Cerrar pedido con integración POS.
