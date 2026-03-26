# POS Offline Validation

Validacion manual para corte real de internet en equipos cliente ya provisionados.

## Objetivo

Confirmar que una caja POS puede seguir cobrando cuando se corta internet y que la venta se sincroniza correctamente al volver la conexion.

## Precondiciones

1. La app debe ejecutarse como build/PWA instalada, no desde `vite`.
2. El equipo debe haber iniciado sesion online al menos una vez.
3. Debe existir una caja abierta y productos sincronizados localmente.
4. Si el flujo usa lotes, preparar un producto con lote unico y otro con multiples lotes.

## Flujo A: Ticket ya creado y corte durante el cobro

1. Entrar al POS online.
2. Agregar productos al carrito.
3. Abrir el modal de cobro.
4. Cortar internet antes de confirmar el pago.
5. Confirmar el pago.

Resultado esperado:
- la UI limpia la venta
- aparece aviso de sincronizacion pendiente
- el contador offline sube en `receipt`
- al volver internet, el recibo queda `paid` sin intervencion manual
- el stock y el pago quedan aplicados una sola vez

## Flujo B: Cobro express en efectivo con internet caido

1. Entrar al POS online y cargar productos.
2. Cortar internet antes del cobro express.
3. Ejecutar cobro express.

Resultado esperado:
- la venta queda encolada offline
- no se pierde el carrito ni queda la caja bloqueada
- al volver internet se crea el recibo y luego se cobra
- el recibo sincronizado queda `paid`

## Flujo C: Corte antes de crear el borrador remoto

1. Entrar al POS online y cargar productos.
2. Cortar internet antes de abrir el cobro.
3. Entrar al flujo normal de cobro.
4. Completar metodo de pago y, si aplica, lotes.

Resultado esperado:
- el modal de cobro abre con lineas locales
- la venta queda encolada completa aunque no exista receipt remoto
- al volver internet se crea el receipt y luego se completa el checkout

## Flujo D: Reconexion tras respuesta perdida

1. Repetir el Flujo A.
2. Restaurar internet.
3. Forzar sincronizacion manual si no ocurre sola.

Resultado esperado:
- si el recibo ya estaba `paid` en servidor, no se intenta cobrar otra vez
- no aparecen duplicados de cobro ni doble descuento de stock

## Flujo E: Apertura de turno sin internet

1. Entrar online al POS con una caja sin turno abierto.
2. Cerrar la app o recargar una vez para confirmar que el equipo ya quedo provisionado.
3. Cortar internet.
4. Abrir el POS e iniciar turno.
5. Cobrar al menos una venta offline.
6. Restaurar internet.

Resultado esperado:
- el turno abre localmente y la caja queda operativa
- el indicador de sincronizacion pendiente sube en `shift`
- al volver internet, primero se crea el turno remoto y despues sincronizan los receipts que dependian de ese turno
- la caja visible en UI termina con `shift_id` real de servidor, no con el temporal

## Flujo F: Cierre de turno sin internet

1. Entrar online con un turno abierto y dejar el equipo provisionado.
2. Cortar internet.
3. Abrir el resumen de cierre de caja.
4. Confirmar el cierre con total contado y, si aplica, perdidas.
5. Restaurar internet.

Resultado esperado:
- el POS permite cerrar caja con resumen cacheado o fallback local
- el turno desaparece como abierto en la UI local
- al volver internet, el cierre pendiente se sincroniza sin reabrir la caja
- si el turno se habia abierto tambien offline, se reconcilia apertura y cierre en orden correcto

## Comprobaciones minimas

- backend: recibo final en estado `paid` y una sola aplicacion de stock
- backend: turno final en estado correcto y sin duplicados de apertura/cierre
- UI: contador offline vuelve a cero tras sincronizar
- operacion: la caja sigue usable para la siguiente venta

## Gaps conocidos

- no cubre un equipo nuevo sin precarga previa
- no cubre emision documental offline completa
- el cierre offline usa resumen cacheado/local cuando no hay backend; debe validarse con caja real y conteo manual
- requiere validacion manual con productos multi-lote en un equipo provisionado
