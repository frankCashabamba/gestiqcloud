# Informe: rutas frontend a endpoints inexistentes (funcionalidad rota)

Fecha: 2026-06-13
Generado tras unificar la convención de rutas FE↔BE (ver `mejoras_frontend_gestiqcloud.md` y plan de unificación).

Estas rutas **ya siguen la convención correcta** (`/api/v1/...` absoluta, baseURL=host) pero apuntan a endpoints que **no existen en el backend**. No son inconsistencias de convención sino **funcionalidad rota o incompleta**: requieren decidir si el endpoint debe crearse en backend, mapearse a otro existente, o si la feature/código está obsoleta.

Verificado contra el volcado real de rutas del backend (770 rutas `/api/v1`, sin doble-prefijo).

## Admin

| Archivo | Ruta(s) FE | Endpoint backend real | Acción sugerida |
|---|---|---|---|
| `services/company-users.ts` (vivo, `CompanyUsers.tsx`) | `/api/v1/admin/tenants/{id}/users`, `/{userId}`, `/{userId}/reset-password`, `users/{userId}/activity` | No existe `admin/tenants/...`. Hay `/api/v1/admin/users/{user_id}/activate\|deactivate\|set-password\|resend-reset` y `/api/v1/admin/companies/{tenant_id}/...` | Decidir: ¿crear CRUD de usuarios por empresa en backend, o reescribir el FE sobre `admin/users` + `admin/companies`? |
| `services/company-settings.ts` (vivo) | `/api/v1/admin/companies/{id}/settings/export`, `/restore-defaults`, `/{module}` | Existe `/api/v1/admin/companies/{tenant_id}/company/settings` (+`/limits`), sin `export\|restore-defaults\|{module}` | Mapear a `company/settings` o crear endpoints export/restore en backend |
| `services/api.ts` → `apiClient.dashboard` (2 usos) | `/api/v1/dashboard_stats`, `/api/v1/dashboard_kpis` | Existe `/api/v1/admin/stats` | Mapear getStats→`admin/stats`; getKpis no tiene destino |
| `services/api.ts` → `apiClient.notifications` (4 usos) | `/api/v1/notifications`, `/{id}` | Solo existe bajo tenant (`/api/v1/tenant/notifications`) | Definir si admin tiene notificaciones propias o reusar otra ruta |
| `services/api.ts` → `apiClient.webhooks` (7 usos) | `/api/v1/webhooks`, `/{id}`, `/{id}/test`, `/{id}/logs` | Solo existe bajo tenant (`/api/v1/tenant/webhooks`) | Definir webhooks admin en backend o reapuntar |
| `modules/country-packs/services.ts` (vivo) | `/api/v1/country-packs`, `/{code}`, `/{code}/validate` | No existe ningún `country-packs` | ¿Crear módulo country-packs en backend o eliminar feature? |
| `packages/endpoints/src/admin.ts` (`ADMIN_USERS`) | `/api/v1/admin/users/{id}`, `/{id}/assign-new-admin` | Hay `admin/users/{user_id}/...` (acciones) pero no GET/PUT `{id}` ni `assign-new-admin` | Verificar consumidores; mapear o crear |

## Vestigios en español (migración es→en del backend) — RESUELTOS

El backend está 100% en inglés (0 rutas en español) y tuvo infraestructura de alias/legacy deprecated (`_wrap_deprecated_router` en `router.py`). Las rutas FE en español dependían de esos alias ya retirados:
- `/api/v1/admin/categorias-gasto` → era código muerto (`CategoriaGastoListSimple/Refactored`), **eliminado**. El servicio vivo ya usa `/api/v1/admin/config/expense-category`.
- `/api/v1/admin/empresas` (default de `createEmpresaService` en `packages/domain`) → era un default **inalcanzable** (admin pasa `ADMIN_COMPANIES.base`, tenant pasa `TENANT_COMPANIES.base`, ambos inglés). **Corregido** el default a `/api/v1/admin/companies`.
- `services/api/recetas.ts` → solo el **nombre del archivo** está en español; las rutas internas usan inglés (`/api/v1/tenant/production/recipes`). Sin problema funcional.

## Notas
- `packages/http-core/src/index.ts`: los defaults `refreshPath='/api/v1/auth/refresh'` y `authExemptSuffixes=['/api/v1/auth/logout'...]` apuntan a rutas genéricas inexistentes, **pero siempre se sobreescriben** por admin (`ADMIN_AUTH.*`) y tenant (`TENANT_AUTH.*`). No son llamadas activas; opcional alinear el default.
- Bases que aparecen "sin match" en la auditoría pero **sí funcionan** (se concatenan con subpaths): `/api/v1/tenant/{crm,production,inventory,printing,reconciliation,restaurant,historical,documents,customers}`, `/api/v1/admin/ui-config`, `/api/v1/admin/importador/routing`, `/api/v1/tenant/auth/mfa`. No requieren acción.
