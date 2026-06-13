# Matriz E2E POS

Fecha: 2026-06-13

## Casos mínimos

| ID | Caso | Estado |
|---|---|---|
| POS-01 | Abrir caja online | Pendiente |
| POS-02 | Vender online efectivo | Parcial |
| POS-03 | Vender online tarjeta | Pendiente |
| POS-04 | Venta offline y sync posterior | Cubierto en unit/offline sync, falta E2E |
| POS-05 | Cierre caja con diferencia | Pendiente |
| POS-06 | No duplicar ticket al reintentar sync | Cubierto en unit/offline sync, falta E2E |
| POS-07 | Emitir documento desde ticket | Pendiente |
| POS-08 | Fallo de red durante pago | Pendiente |
| POS-09 | Borrar ticket borrador | Pendiente |
| POS-10 | Validar stock/lote al vender | Parcial |

## Contrato frontend/backend

- Frontend puede previsualizar totales.
- Backend confirma totales fiscales, stock, pagos y estado final.
- Cada checkout debe tener idempotency key o `client_request_id`.
- Offline sync no debe cobrar dos veces ni descontar stock dos veces.

## Evidencia actual

- `apps/tenant/src/modules/pos/offlineSync.test.ts` cubre sync offline, checkout existente, venta express offline e idempotencia.
- `e2e/pos.spec.ts` y `e2e/pos_checkout.spec.ts` cubren smoke de interfaz y checkout básico.
