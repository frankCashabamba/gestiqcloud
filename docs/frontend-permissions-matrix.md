# Matriz de permisos frontend

Fecha: 2026-06-13

Esta matriz define los permisos que la UI debe usar por mÃ³dulo. No sustituye la autorizaciÃ³n backend: cada fila debe mantenerse alineada con `require_permission(...)`, `require_scope(...)` o el mecanismo equivalente del router backend.

Estados:

- OK: frontend y backend tienen una protecciÃ³n equivalente.
- Parcial: hay protecciÃ³n, pero no es granular o falta confirmar roles.
- Gap: la UI o el backend no protegen con el permiso esperado.

## Roles operativos mÃ­nimos

| Rol | Alcance esperado |
|---|---|
| `admin` | Acceso completo de tenant, roles, configuraciÃ³n, permisos, fiscalidad y mÃ³dulos crÃ­ticos. |
| `encargado` | GestiÃ³n operativa: ventas, compras, inventario, POS, reportes bÃ¡sicos y usuarios no administrativos segÃºn tenant. |
| `cajera` | POS, caja, recibos, devoluciones permitidas y lectura de productos/clientes necesaria para venta. |
| `panadero` | ProducciÃ³n, recetas, consumo de materias primas e inventario operativo limitado. |

## Matriz tenant

| MÃ³dulo | Read | Create | Update | Delete | Especiales | ProtecciÃ³n frontend | Backend observado | Estado |
|---|---|---|---|---|---|---|---|---|
| `users` | `users:read` | `users:create` | `users:update` | `users:delete` | `users:set_password`, `roles:*` | `ProtectedRoute` y botones | Scope tenant + roles endpoints | Parcial |
| `settings` | `settings:read` | - | `settings:write` | - | `settings:security`, `settings:billing` si se separan | `ProtectedRoute(settings:read)` | Scope tenant/admin segÃºn endpoint | Parcial |
| `templates` | `templates:read` | - | `templates:manage` | - | `templates:write` legacy | `ProtectedRoute(templates:manage)` | Scope tenant/admin | Parcial |
| `webhooks` | `webhooks:read` | `webhooks:manage` | `webhooks:manage` | `webhooks:manage` | test/retry deliveries | `ProtectedRoute(webhooks:manage)` y botones | Scope tenant; revisar granularidad | Parcial |
| `notifications` | `notifications:read` | `notifications:manage` | `notifications:manage` | `notifications:manage` | mark-read, archive, templates | `ProtectedRoute(notifications:read)` y botones manage | `require_permission(notifications:read/manage)` | OK |
| `products` | `products:read` | `products:create` | `products:update` | `products:delete` | purge, merge duplicates, labels | `ProtectedRoute` por rutas crÃ­ticas | Scope tenant; revisar acciones especiales | Parcial |
| `inventory` | `inventory:read` | `inventory:create` | `inventory:update` | - | `inventory:adjust`, `inventory:manage-alerts` | `ProtectedRoute` y acciones | Scope tenant; endpoints sensibles deben exigir permiso | Parcial |
| `pos` | `pos:read` | `pos:write` | `pos:write` | - | `pos:cashier`, `pos.shift.open`, `pos.shift.close`, `pos.receipt.refund`, `pos.receipt.pay` | `ProtectedRoute(pos:read)` | Backend usa permisos granulares con punto y aliases `:`/`.` en guards | OK |
| `sales` | `sales:read` | `sales:create` | `sales:update` | `sales:delete` | pay, invoice, promotions | `ProtectedRoute` por ruta/acciÃ³n | Backend usa `sales.order.pay` en pagos | Parcial |
| `billing` | `billing:read` | `billing:create` | `billing:update` | `billing:delete` | `billing:send`, `billing:pay` | `ProtectedRoute` | Scope tenant; e-invoicing separado | Parcial |
| `einvoicing` | `einvoicing:read` | - | - | - | `einvoicing:send`, `einvoicing:download`, `einvoicing:retry` | `ProtectedRoute` | Scope tenant; revisar send/retry granular | Parcial |
| `purchases` | `purchases:read` | `purchases:create` | `purchases:update` | `purchases:delete` | receive | `ProtectedRoute` | Scope tenant | Parcial |
| `expenses` | `expenses:read` | `expenses:create` | `expenses:update` | `expenses:delete` | pay, journal integration | `ProtectedRoute` | Algunas acciones usan permisos contables | Parcial |
| `customers` | `customers:read` | `customers:create` | `customers:update` | `customers:delete` | import/export | `ProtectedRoute` | Scope tenant | Parcial |
| `suppliers` | `suppliers:read` | `suppliers:create` | `suppliers:update` | `suppliers:delete` | bank data visibility | `ProtectedRoute` | Scope tenant | Parcial |
| `crm` | `crm:read` | `crm:create` | `crm:update` | `crm:delete` | convert lead, manage pipeline | `ProtectedRoute` y acciones | Scope tenant | Parcial |
| `quotes` | `quotes:read` | `quotes:create` | `quotes:update` | `quotes:delete` | approve, convert | `ProtectedRoute` | Backend usa `quotes.manage` con aliases frontend | OK |
| `reports` | `reports:read` | - | - | - | `reports:export` | `ProtectedRoute` | Scope tenant; reportes avanzados revisar | Parcial |
| `accounting` | `accounting:read` | `accounting:entry` | `accounting:adjust` | - | `accounting.entry.create`, `accounting.entry.post`, `accounting.entry.cancel`, `accounting.period.manage` | `ProtectedRoute(accounting:read)` | Backend usa permisos granulares con punto y aliases frontend | OK |
| `finances` | `finances:read` | - | - | - | `finances:forecast`, `finances:report`, cash/bank write | `ProtectedRoute` | Backend usa permisos finance para cashbox | Parcial |
| `reconciliation` | `reconciliation:read` | - | `reconciliation:match` | - | `reconciliation:resolve` | `ProtectedRoute` | Scope tenant; providers/webhooks revisar | Parcial |
| `productions` | `manufacturing:read` | `manufacturing:create` | `manufacturing:update` | `manufacturing:delete` | start/complete/cancel order | `ProtectedRoute` | Scope tenant | Parcial |
| `hr` | `hr:read` | - | `hr:manage` | - | payroll, timekeeping, vacations | `ProtectedRoute` | Scope tenant | Parcial |
| `importador` | `importer:use` | `importer:use` | `importer:use` | - | confirm, route, save destination, purge | `ProtectedRoute` pendiente de confirmar por ruta | Scope tenant en routers importador | Parcial |
| `historical` | `historical:read` | `historical:import` | - | `historical:delete` | upload, dedupe | `ProtectedRoute` | Scope tenant | Parcial |
| `analytics` | `analytics:read` | - | - | - | KPIs por sector | `ProtectedRoute` | Scope tenant | Parcial |
| `copilot` | `copilot:read` | - | - | - | chat, stream, feedback, metrics | `ProtectedRoute` | IA usa rate limit/tenant; permisos granulares revisar | Parcial |
| `restaurant` | `restaurant:read` | `restaurant:manage` | `restaurant:manage` | - | KDS, close order, POS integration | `ProtectedRoute` | Backend tiene permisos KDS granulares | Parcial |

## Gaps prioritarios

1. Revisar `templates` y `webhooks`: frontend usa `:manage` y backend conserva permisos historicos; hay aliases frontend, pero falta granularidad completa por accion.
2. Ampliar granularidad de `sales`, `billing`, `einvoicing`, `inventory` y `reports` cuando se endurezcan esos endpoints backend.
3. Ejecutar E2E de permisos con fixtures reales de `admin`, `encargado`, `cajera` y `panadero`.

## Cierres 2026-06-13

- `require_permission` backend acepta permisos planos y anidados, con aliases `:`/`.` para `pos`, `accounting` y `quotes`.
- `notifications` tiene `require_permission("notifications:read")` para lectura y `require_permission("notifications:manage")` para acciones de escritura.
- Los seeds de permisos incluyen POS, accounting, quotes y notifications.
- Los presets operativos actualizan permisos POS para `Cajera` y `Encargado`.
- La suite frontend tiene tests unitarios de normalizacion de permisos y E2E smoke para rutas protegidas.

## Regla de mantenimiento

Cuando se cree o cambie una pantalla sensible:

1. AÃ±adir/actualizar permiso en manifest/module.json.
2. AÃ±adir label i18n en `locales/*/permissions.json`.
3. Proteger ruta con `ProtectedRoute` si muestra datos sensibles.
4. Proteger botones destructivos con `ProtectedButton` o `can(...)`.
5. Confirmar backend con `require_permission(...)` o justificar por quÃ© solo aplica `require_scope("tenant")`.
6. AÃ±adir prueba de acceso permitido/denegado si el mÃ³dulo es crÃ­tico.
