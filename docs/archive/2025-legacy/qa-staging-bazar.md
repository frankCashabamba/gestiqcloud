# QA Staging — Tenant Bazar

Objetivo: validar funcional funcional para el Go‑Live piloto.

## Alcance
- Tenancy + RLS activos y verificados cruzando tenants.
- Ventas: pedido → confirmación (reserva) → entrega (salida) → factura (borrador) → emisión (numeración atómica).
- Inventario multi‑almacén: reservas / salidas / transferencias / cycle count.
- POS: apertura turno → venta → cobro → post → cierre turno (arqueo).
- E‑invoicing (staging): SRI (EC) `AUTHORIZED` y SII (ES) `ACCEPTED`.
- Plantillas Bazar activas; overlays dentro de límites.
- Copiloto tenant-first: consultas de sólo lectura y creación de borradores (pedido/factura/traspaso).

## Preparación
- Render `gestiqcloud-api` y `gestiqcloud-worker` desplegados en `main`.
- Secrets configurados: `DATABASE_URL`, `JWT_SECRET_KEY`, `SECRET_KEY`, `REDIS_URL`, `CELERY_RESULT_BACKEND`.
- Beat opcional: `gestiqcloud-beat` con `EINV_TENANT_ID` del piloto.
- `RUN_LEGACY_MIGRATIONS=1`, `RUN_RLS_APPLY=1` activos.

## Casos de prueba
1) RLS
   - Login Tenant A y B. Verifica que `/api/v1/inventario/stock` no cruza filas.
2) Ventas/Inventario
   - Crea pedido con 2 items; `POST /sales_orders/{id}/confirm` crea reservas (movimientos tentative=true).
   - `POST /deliveries` y `/deliver` generan `issue` y rebajan `stock_items`.
   - Emite factura: estado `emitida` y número con `assign_next_number` sin colisiones en concurrencia.
3) PDFs
   - `GET /facturacion/{id}/pdf` descarga; Totales correctos.
4) POS
   - Crea register con almacén por defecto, abre shift, ticket draft, añade items, cobro `cash`, `post` ticket; cierra shift y valida arqueo.
5) E‑invoicing
   - EC: `/einvoicing/send/{invoice_id}` con `{country:"EC"}` → `AUTHORIZED` (stub/worker).
   - ES: `/einvoicing/send/0` con `{country:"ES","period":"2025Q4"}` → `ACCEPTED`.
6) Plantillas/Overlays
   - Asigna paquete `bazar v1` al tenant; `GET /templates/ui-config` contiene columnas SKU/Name/Price.
   - Crea overlay válido (<15 campos, <8KB, profundidad ≤2) y activa; verifica cambio en `ui-config`.
7) Copiloto
   - `/ai/ask` con `ventas_mes`, `top_productos`, `stock_bajo` responde tarjetas.
   - `/ai/act` crea borrador de factura y pedido; nunca `postea`.

## Criterios PASS/GO
- RLS correcto (0 fugas), numeración atómica sin colisiones, inventario consistente tras entregas y POS, e‑invoicing retorna estados esperados, overlays activos sin romper UI, copilot no comete acciones fuera de borradores.

## Rollback
- Si migraciones fallan: revertir despliegue y restaurar backup de DB más reciente.
- Desactivar Beat (`ENABLE_EINVOICING_BEAT=0`) si hay efectos no deseados.
