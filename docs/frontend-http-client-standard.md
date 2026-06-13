# Estándar de cliente HTTP frontend

Fecha: 2026-06-13

## Decisión

El patrón objetivo es:

- Tenant: usar `tenantApi` para módulos nuevos y migraciones.
- Admin: usar el cliente compartido de Admin basado en `@shared/http`.
- Endpoints: usar `apps/packages/endpoints` para rutas canónicas.
- `apiFetch`: queda como compatibilidad legacy y se migra por fases.
- `fetch` directo: solo permitido para streaming/SSE, descargas especiales o integraciones documentadas.

## Reglas

1. Ningún módulo nuevo debe construir URLs con strings si existe helper en `apps/packages/endpoints`.
2. Todo 401/refresh debe pasar por el cliente compartido.
3. Todo endpoint tenant debe usar rutas `/api/v1/tenant/...` o helper equivalente.
4. Los errores HTTP deben convertirse a mensajes UI con `getErrorMessage` o helper común.
5. Las excepciones deben dejar comentario corto junto al uso.

## Migración por prioridad

| Prioridad | Área | Motivo |
|---|---|---|
| Alta | POS, Billing, E-invoicing, Importador | Pagos, fiscalidad, datos críticos. |
| Alta | Settings, Users, Permissions | Seguridad y configuración tenant. |
| Media | Inventory, Production, Accounting | Consistencia de stock/costes/contabilidad. |
| Baja | Dashboards, reports simples | Menor riesgo transaccional. |

## Cierres 2026-06-13

- POS mantiene `tenantApi` y migra rutas principales a helpers `TENANT_POS` y `TENANT_DOCUMENTS`.
- Billing `ProductLineInput` usa `TENANT_PRODUCTS` y elimina el `any` del fetch de productos.
- Importador usa helpers `TENANT_IMPORTADOR` tambien para staging, iterations y review sessions.
- Se mantiene la excepcion de streaming en importador mediante `EventSource`, con token resuelto por el flujo existente.

## Excepciones permitidas

| Caso | Permitido | Condición |
|---|---|---|
| SSE/streaming IA | `fetch` directo | Debe resolver token igual que el cliente compartido. |
| Descarga binaria | `fetch` o `tenantApi` con responseType | Debe manejar 401 y errores. |
| Compatibilidad legacy | `apiFetch` | Debe tener ticket o entrada de migración. |

## Checklist para migrar un servicio

- Reemplazar string endpoint por helper de `apps/packages/endpoints`.
- Usar `tenantApi.get/post/put/delete` o cliente admin equivalente.
- Mantener headers offline si el flujo los necesita.
- Añadir test unitario si hay normalización de payload.
- Ejecutar typecheck de la app afectada.
