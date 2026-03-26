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

## Flujo C: Reconexion tras respuesta perdida

1. Repetir el Flujo A.
2. Restaurar internet.
3. Forzar sincronizacion manual si no ocurre sola.

Resultado esperado:
- si el recibo ya estaba `paid` en servidor, no se intenta cobrar otra vez
- no aparecen duplicados de cobro ni doble descuento de stock

## Comprobaciones minimas

- backend: recibo final en estado `paid` y una sola aplicacion de stock
- UI: contador offline vuelve a cero tras sincronizar
- operacion: la caja sigue usable para la siguiente venta

## Gaps conocidos

- no cubre un equipo nuevo sin precarga previa
- no cubre emision documental offline completa
- si el corte ocurre antes de crear el borrador del ticket, ese flujo todavia requiere validacion adicional
