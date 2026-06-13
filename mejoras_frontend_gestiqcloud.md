# Mejoras Frontend â€” GestiQCloud

Fecha: 2026-06-13  
Ãmbito: `apps/admin`, `apps/tenant`, `apps/packages`  
Excluido: `apps/backend`

---

## 1. Veredicto ejecutivo

El frontend de GestiQCloud tiene una base sÃ³lida para SaaS: separaciÃ³n entre Admin y Tenant, React/Vite/TypeScript, mÃ³dulos dinÃ¡micos, PWA, permisos por mÃ³dulo, POS offline, importador avanzado, configuraciÃ³n por tenant y paquetes compartidos.

Pero todavÃ­a no estÃ¡ al nivel de frontend SaaS profesional estable. El problema no es que falten pantallas, sino que hay diferencias de madurez entre mÃ³dulos, documentaciÃ³n desalineada, mezcla de clientes HTTP, rutas inconsistentes, uso de `any` en zonas sensibles, mÃ³dulos sin protecciÃ³n explÃ­cita y lÃ³gica crÃ­tica offline demasiado concentrada en frontend.

Nota global frontend actual: **6.8/10**

Prioridad real:

1. Endurecer seguridad y auth/offline.
2. Unificar cliente HTTP y manejo de errores.
3. Normalizar mÃ³dulos, rutas, permisos y documentaciÃ³n.
4. AÃ±adir tests E2E mÃ­nimos para mÃ³dulos crÃ­ticos.
5. Limpiar documentaciÃ³n inflada o desactualizada.
6. Convertir `apps/packages` en capa compartida clara y mantenible.

---

## 1.1 Seguimiento de ejecuciÃ³n

Actualizado: 2026-06-13

Este bloque resume lo que ya se tocÃ³ y lo que queda por hacer para continuar el plan sin perder contexto.

### Hecho

| ID | Estado | Que se hizo | Archivos principales |
|---|---|---|---|
| F-01 | Hecho | Scripts frontend documentados y alineados. | `docs/frontend-commands.md` |
| F-02 | Hecho operativo | Capa compartida formalizada y documentada. | `apps/packages/README.md` |
| F-03 | Hecho critico | POS/Billing/Importador usan `tenantApi` y helpers compartidos en rutas criticas. | `docs/frontend-http-client-standard.md`, `apps/packages/endpoints`, servicios criticos |
| F-04 | Hecho auditoria | Riesgos de auth offline documentados; queda decision de cifrado/revocacion. | `docs/security/frontend-offline-auth.md` |
| F-05 | Hecho | Eliminado `any` sensible en ProtectedRoute/auth. | `apps/admin/src/app/ProtectedRoute.tsx`, `apps/tenant/src/app/ProtectedRoute.tsx` |
| F-06 | Hecho | `notifications`, webhooks, templates y settings tienen proteccion interna. | `apps/tenant/src/modules/notifications/Routes.tsx` |
| F-07 | Hecho parcial | CRUD basico normalizado a `new/edit` con redirects legacy `nuevo/editar`. | `docs/frontend-route-conventions.md`, rutas CRUD |
| F-08 | Hecho operativo | Matriz POS documentada; tests profundos quedan ligados a fixtures. | `docs/pos-e2e-matrix.md` |
| F-09 | Hecho hardening | Importador filtra raw/debug JSON y marca origen de campos visibles. | `docs/importador-critical-checklist.md`, `DocumentDetail.tsx`, `ReprocessPanel.tsx` |
| F-10 | Hecho | Documentacion inflada limpiada y READMEs normalizados. | READMEs y docs principales |
| F-11 | Hecho | Todos los modulos tenant tienen README minimo. | `apps/tenant/src/modules/*/README.md` |
| F-12 | Hecho reforzado | Matriz creada, aliases `:`/`.` implementados y `notifications` protegido en backend. | `docs/frontend-permissions-matrix.md`, `authz.py`, notifications backend |
| F-13 | Hecho | `ModuleErrorBoundary` por modulo. | `ModuleErrorBoundary.tsx`, `ModuleLoader.tsx` |
| F-14 | Hecho | Metadata `status/maturity/risk` y badges en UI. | `module.json`, panel de modulos |
| F-15 | Hecho inicial reforzado | E2E importador/permisos ampliados; fixtures reales siguen pendientes. | `e2e/importador.spec.ts`, `e2e/permissions.spec.ts` |

### Verificaciones realizadas

- Tenant typecheck pasa con `cmd /c npm --prefix apps/tenant run typecheck`.
- Todos los modulos tenant tienen README minimo.
- Todos los `module.json` tienen `status`, `maturity` y `risk`.
- POS/Billing/Importador no muestran usos legacy detectados de `apiFetch`, `fetch` directo o strings criticos en las rutas migradas.
- `notifications` tiene `require_permission` backend y permisos frontend/locales/module.json.
- CRUD basico conserva redirects legacy y links internos apuntan a `new/edit`.
- Importador filtra campos raw/debug en vista normal y tiene E2E anti-exposicion.

### Deuda tecnica posterior

| ID | Estado | Proximo paso recomendado |
|---|---|---|
| F-04 | Riesgo abierto | Implementar cifrado/reduccion de token offline, politica por tenant y revocacion al volver online. |
| F-08 | Deuda critica POS | Ejecutar E2E reales con fixtures: caja, ticket, pago, sync offline, refund y stock. |
| F-12 | Deuda granular restante | Endurecer permisos backend de templates/webhooks/sales/billing/einvoicing/inventory/reports cuando se cierren esos routers. |
| F-15 | Deuda QA | Ejecutar Playwright contra entorno con credenciales/fixtures y endurecer asserts de permitido/denegado por rol. |

### Siguiente bloque sugerido

1. Ejecutar suite backend de seguridad y frontend unit tests relevantes en CI/local completo.
2. Preparar fixtures E2E por rol (`admin`, `encargado`, `cajera`, `panadero`).
3. Cerrar auth offline en codigo: cifrado, expiracion por tenant y revocacion online.
4. Convertir matriz POS en E2E transaccionales reales.

---

## 2. Estado actual por Ã¡rea

| Ãrea | Nota | Estado |
|---|---:|---|
| Admin app | 6.5/10 | Correcta, pero menos madura que Tenant |
| Tenant app | 7/10 | Buena arquitectura SaaS modular |
| MÃ³dulos Tenant | 6.8/10 | Core potente, madurez desigual |
| Packages compartidos | 5.8/10 | Ãštiles, pero falta estructura limpia |
| Auth/refresh/CSRF | 6.5/10 | Funciona, pero hay duplicidad y complejidad |
| Offline/PWA | 6/10 | Potente, pero necesita auditorÃ­a |
| Testing frontend | 5/10 | Hay scripts, falta cobertura real/E2E |
| DocumentaciÃ³n frontend | 5.5/10 | Existe, pero estÃ¡ desalineada |

---

## 3. Hallazgos principales

## F-01 â€” DocumentaciÃ³n frontend desalineada con scripts reales

Estado: HECHO 2026-06-13  
Severidad: MEDIA  
Ãrea: `docs/frontend-commands.md`, `apps/admin/package.json`, `apps/tenant/package.json`

### Problema

La documentaciÃ³n indica que no hay comandos definidos de lint/format y que `typecheck/build` son la garantÃ­a mÃ­nima, pero `admin` y `tenant` ya tienen scripts de lint, test y coverage.

### Impacto

Un desarrollador puede no ejecutar validaciones importantes antes de subir cÃ³digo.

### RecomendaciÃ³n

Actualizar `docs/frontend-commands.md`:

```md
## ValidaciÃ³n recomendada

Admin:
- npm run typecheck
- npm run lint
- npm run test:run
- npm run build

Tenant:
- npm run check
- npm run build
```

### Resultado revisado

- `docs/frontend-commands.md` ya lista `typecheck`, `lint`, `test:run`, `build` y `check`.
- Admin y Tenant tienen scripts reales en `package.json`.
- No queda acciÃ³n inmediata para F-01 salvo mantener esta doc sincronizada cuando cambien scripts.

---

## F-02 â€” `apps/packages` no estÃ¡ formalizado como workspace real

Estado: HECHO OPERATIVO 2026-06-13  
Severidad: ALTA  
Ãrea: `apps/packages/*`, `vite.config.ts`, alias compartidos

### Problema

Admin y Tenant dependen de alias como:

- `@shared/http`
- `@shared/endpoints`
- `@shared/auth-core`
- `@shared/ui`
- `@api-types`
- `@gestiq/mini-zod`

Pero la capa `apps/packages` parece mÃ¡s una carpeta de cÃ³digo compartido que paquetes versionados/workspace formal.

### Impacto

Puede haber:

- imports frÃ¡giles,
- dependencias duplicadas,
- tipos inconsistentes,
- errores difÃ­ciles de detectar en CI,
- acoplamiento fuerte entre Admin/Tenant.

### RecomendaciÃ³n

Crear una estructura clara:

```text
apps/packages/
  README.md
  ui/
    README.md
    package.json
    src/
  http-core/
    README.md
    package.json
    src/
  endpoints/
    README.md
    package.json
    src/
  api-types/
    README.md
    package.json
    src/
  auth-core/
    README.md
    package.json
    src/
```

Y documentar:

- quÃ© paquete puede importar a cuÃ¡l,
- quÃ© paquete es estable,
- quÃ© paquete es interno,
- quÃ© alias usa cada app.

### Resultado revisado

- Existe `apps/packages/README.md` con listado de paquetes, consumo, versionado y pendientes.
- Existen paquetes compartidos (`ui`, `auth-core`, `http-core`, `endpoints`, `api-types`, etc.).
- Sigue como deuda tÃ©cnica formalizar workspace/build/test por paquete y ownership explÃ­cito.

---

## F-03 â€” Cliente HTTP duplicado o parcialmente solapado

Estado: HECHO OPERATIVO 2026-06-13  
Severidad: ALTA  
Ãrea: `apps/admin/src/lib/http.ts`, `apps/tenant/src/lib/http.ts`, `apps/tenant/src/shared/api/client.ts`, `apps/packages/shared/src/httpTenant.ts`

### Problema

Hay varios caminos para hacer requests:

- `apiFetch` tenant.
- `tenantApi` basado en `createSharedClient`.
- HTTP client admin legacy.
- Shared client desde `@shared`.

### Impacto

Riesgo de:

- refresh duplicado,
- CSRF inconsistente,
- errores 401 tratados distinto,
- headers diferentes segÃºn mÃ³dulo,
- bugs difÃ­ciles de reproducir.

### RecomendaciÃ³n

Definir un Ãºnico patrÃ³n:

```text
apps/packages/http-core/
  createTenantClient.ts
  createAdminClient.ts
  errors.ts
  csrf.ts
  refresh.ts
```

Regla:

- mÃ³dulos nuevos solo usan `tenantApi`.
- `apiFetch` queda legacy y se migra por fases.
- prohibir `fetch` directo salvo excepciones documentadas.

### Resultado revisado

- Hay avances: `tenantApi`, `apiFetch`, `http-core`, `httpTenant` y `apps/packages/endpoints`.
- Sigue habiendo mezcla de `fetch`, `apiFetch`, `tenantApi` y llamadas directas con strings.
- PatrÃ³n Ãºnico definido en `docs/frontend-http-client-standard.md`; queda deuda de migraciÃ³n por fases.

---

## F-04 â€” Auth Tenant demasiado compleja y con riesgo offline

Estado: HECHO AUDITORÃA / RIESGO ABIERTO 2026-06-13  
Severidad: ALTA  
Ãrea: `apps/tenant/src/auth/AuthContext.tsx`, `offlineAuth`, `offlineStore`

### Problema

Tenant combina:

- `sessionStorage`,
- `localStorage`,
- IndexedDB/offline snapshot,
- login offline,
- token fallback,
- refresh online,
- recuperaciÃ³n de perfil offline.

Esto es potente, pero sensible.

### Riesgo

Si credenciales o tokens quedan persistidos de forma insegura, es un punto crÃ­tico.

### RecomendaciÃ³n

Crear auditorÃ­a especÃ­fica:

```text
docs/security/frontend-offline-auth.md
```

Debe responder:

- Â¿Se guarda password plano? Si sÃ­, eliminar.
- Â¿Se cifra el snapshot offline?
- Â¿CuÃ¡ndo expira una sesiÃ³n offline?
- Â¿CÃ³mo se revoca offline si el usuario fue deshabilitado?
- Â¿QuÃ© datos se guardan en IndexedDB?
- Â¿QuÃ© pasa en un dispositivo compartido?

### Regla recomendada

Para producciÃ³n:

- offline login solo para roles permitidos,
- expiraciÃ³n corta,
- no guardar password plano,
- cifrado con clave derivada,
- logout borra todo,
- opciÃ³n admin para desactivar offline por tenant.

### Resultado revisado

- `offlineAuth.ts` hashea password con salt y expira credenciales a 30 dÃ­as.
- No guarda password plano.
- Guarda token y snapshot offline en IndexedDB; no hay cifrado fuerte del snapshot completo.
- No se encontrÃ³ polÃ­tica admin por tenant para desactivar offline login ni revocaciÃ³n offline robusta si el usuario fue deshabilitado.

---

## F-05 â€” Uso de `any` en zonas sensibles

Estado: HECHO 2026-06-13  
Severidad: MEDIA  
Ãrea: Protected routes, services, POS, importador

### Problema

Hay casts como:

```tsx
useAuth as any
```

TambiÃ©n hay tipos `any` en POS, importador y servicios complejos.

### Impacto

Se pierde protecciÃ³n TypeScript justo en zonas crÃ­ticas: permisos, auth, pagos, documentos, importador.

### RecomendaciÃ³n

Crear tipos comunes:

```ts
export type AuthHookResult = {
  token: string | null
  loading: boolean
  profile: unknown | null
  refresh: () => Promise<boolean>
}
```

Y hacer que `ProtectedRoute` acepte una interfaz tipada, no `any`.

### Resultado aplicado

- `ProtectedRoute` de Admin y Tenant ya delega en el componente compartido sin cast `as any`.
- La superficie compartida de auth queda tipada para el uso de rutas protegidas.
- Pendiente fuera del alcance de este cierre: auditar otros `any` en POS, importador y servicios complejos.

---

## F-06 â€” MÃ³dulos simples sin protecciÃ³n explÃ­cita

Estado: HECHO 2026-06-13  
Severidad: ALTA  
Ãrea: `webhooks`, `templates`, posibles mÃ³dulos secundarios

### Problema

Algunos mÃ³dulos tienen protecciÃ³n por el `ModuleLoader` exterior, pero dentro no declaran `ProtectedRoute` propio.

Ejemplo:

```tsx
export default function WebhooksRoutes() {
  return (
    <Routes>
      <Route path="/" element={<SubscriptionsList />} />
    </Routes>
  )
}
```

### Impacto

Si en el futuro se reutiliza la ruta desde settings o se cambia el layout, puede quedar una pantalla sensible sin control interno.

### RecomendaciÃ³n

AÃ±adir protecciÃ³n interna mÃ­nima:

```tsx
<ProtectedRoute permission="webhooks:read">
  <Routes>...</Routes>
</ProtectedRoute>
```

Aplicar a:

- `webhooks`
- `templates`
- `notifications`
- cualquier mÃ³dulo cargado dentro de settings.

### Resultado revisado

- AcciÃ³n/rutas revisadas: `webhooks`, `templates`, `notifications`, `settings`.
- ProtecciÃ³n frontend encontrada: `webhooks`, `templates`, `settings` y `notifications` usan `ProtectedRoute`.
- Mismatch pendiente documentado en `docs/frontend-permissions-matrix.md`: backend de notifications usa tenant/auth sin permiso granular observado.

---

## F-07 â€” Inconsistencia de rutas en espaÃ±ol e inglÃ©s

Estado: HECHO OPERATIVO 2026-06-13  
Severidad: MEDIA  
Ãrea: mÃ³dulos tenant

### Problema

Hay mÃ³dulos con rutas en espaÃ±ol:

```text
nuevo
editar
```

Y otros en inglÃ©s:

```text
new
edit
```

Ejemplo:

- `expenses`: `nuevo`, `editar`
- `purchases`: `new`, `edit`

### Impacto

UX inconsistente, documentaciÃ³n confusa y mÃ¡s ramas de soporte.

### RecomendaciÃ³n

Elegir estÃ¡ndar.

Para producto hispano/Ecuador/EspaÃ±a recomiendo:

```text
nuevo
:id/editar
```

Mantener redirects legacy:

```tsx
<Route path="new" element={<Navigate to="../nuevo" replace />} />
<Route path=":id/edit" element={<Navigate to="../:id/editar" replace />} />
```

### Resultado revisado

- No aparecen rutas `nuevo/editar` de forma generalizada en mÃ³dulos CRUD bÃ¡sicos.
- Siguen existiendo rutas mixtas en `accounting`, `hr`, `productions`, `finances`, `reports` e `importador`.
- Hay aliases Ãºtiles (`vacaciones` -> `vacations`, `planner` -> `planificacion`), y la convenciÃ³n formal queda en `docs/frontend-route-conventions.md`.

---

## F-08 â€” POS tiene lÃ³gica crÃ­tica excesiva en frontend

Estado: HECHO OPERATIVO 2026-06-13  
Severidad: ALTA  
Ãrea: `apps/tenant/src/modules/pos`

### Problema

POS gestiona:

- cajas,
- turnos,
- apertura/cierre,
- tickets,
- pagos,
- documentos,
- offline queue,
- sincronizaciÃ³n,
- cache,
- backfill,
- conversiÃ³n a factura.

Es uno de los mÃ³dulos mÃ¡s avanzados, pero tambiÃ©n el mÃ¡s peligroso.

### Riesgos

- tickets duplicados,
- descuadres de caja,
- pagos offline mal sincronizados,
- stock desfasado,
- facturas creadas dos veces,
- cierre de turno inconsistente.

### RecomendaciÃ³n

Crear matriz de tests E2E POS:

```text
POS-01 abrir caja online
POS-02 vender online efectivo
POS-03 vender online tarjeta
POS-04 venta offline y sync posterior
POS-05 cierre caja con diferencia
POS-06 no duplicar ticket al reintentar sync
POS-07 emitir documento desde ticket
POS-08 fallo de red durante pago
POS-09 borrar ticket borrador
POS-10 validar stock al vender
```

AdemÃ¡s:

- mover cÃ¡lculos fiscales crÃ­ticos al backend,
- frontend solo previsualiza,
- backend confirma totales,
- usar idempotency keys en pagos/tickets.

### Resultado revisado

- POS ya estÃ¡ parcialmente separado en `POSView`, hooks, services, `offlineSync` y componentes.
- Hay tests unitarios de sync offline e idempotencia en `apps/tenant/src/modules/pos/offlineSync.test.ts`.
- Sigue habiendo lÃ³gica crÃ­tica en frontend: checkout offline, pagos, stock selections, turnos, drafts y persistencia local.
- Matriz y contrato quedan en `docs/pos-e2e-matrix.md`; queda deuda de convertirlos en E2E completos.

---

## F-09 â€” Importador necesita tratamiento de mÃ³dulo crÃ­tico

Estado: HECHO OPERATIVO 2026-06-13  
Severidad: ALTA  
Ãrea: `apps/tenant/src/modules/importador`

### Problema

Importador maneja:

- documentos,
- OCR/IA,
- datos extraÃ­dos,
- datos confirmados,
- routing,
- destinos,
- facturas/proveedores/gastos/productos,
- revisiÃ³n asistida.

No puede tratarse como CRUD normal.

### Riesgos

- guardar documento en destino incorrecto,
- mostrar datos sensibles,
- confirmar datos errÃ³neos,
- mezclar documentos entre tenants si backend falla,
- demasiada confianza en IA.

### RecomendaciÃ³n

AÃ±adir checklist visible por documento:

```text
- Origen del dato: OCR / IA / usuario / regla
- Confianza
- Campos obligatorios
- Destino sugerido
- AcciÃ³n destructiva o reversible
- Usuario que confirma
- Timestamp de confirmaciÃ³n
```

Y en frontend:

- evitar mostrar raw AI JSON salvo modo debug,
- marcar campos derivados por IA,
- confirmaciÃ³n explÃ­cita antes de guardar en destino,
- historial de cambios visible.

### Resultado revisado

- Hay revisiÃ³n humana, `confirmDocument`, `SaveDocumentModal`, candidatos de destino y `confirmation_required`.
- Hay tests sobre `SaveDocumentModal`.
- Se muestra confianza y hay avisos de revisiÃ³n.
- Checklist crÃ­tico queda en `docs/importador-critical-checklist.md`; queda deuda de hardening UI para raw/debug JSON y origen de campos.

---

## F-10 â€” DocumentaciÃ³n de mÃ³dulos demasiado optimista

Estado: HECHO 2026-06-13  
Severidad: MEDIA  
Ãrea: READMEs de mÃ³dulos

### Problema

Algunos documentos usan lenguaje poco profesional:

```text
110% completitud
```

O listan muchas capacidades sin separar:

- implementado,
- parcial,
- pendiente,
- mock,
- dependiente de backend.

### Impacto

Da sensaciÃ³n de humo aunque el producto tenga buena base.

### RecomendaciÃ³n

Formato estÃ¡ndar para cada mÃ³dulo:

```md
# MÃ³dulo X

Estado: Activo / Beta / Parcial / Legacy
Madurez: 1-5
Owner: Frontend/Backend
Riesgo: Bajo/Medio/Alto

## Implementado
- ...

## Parcial
- ...

## Pendiente
- ...

## Endpoints usados
- ...

## Permisos
- ...

## Tests mÃ­nimos
- ...
```

### Resultado aplicado

- READMEs normalizados con estado, madurez, owner, riesgo, implementado, parcial, pendiente, endpoints, permisos y tests mÃ­nimos en mÃ³dulos crÃ­ticos.
- Eliminado lenguaje inflado en docs y READMEs principales (`110%`, `100%`, `âœ… Completo`, `MÃ³dulo completo`).
- `docs/PLAN_MAESTRO_DESARROLLO.md` ya separa cobertura funcional de preparaciÃ³n productiva.
- `docs/plan-produccion-parches-vs-bloqueos.md` usa lenguaje de cobertura/validaciÃ³n, no certificaciÃ³n absoluta.

---

## F-11 â€” MÃ³dulos sin README o documentaciÃ³n mÃ­nima

Estado: HECHO 2026-06-13  
Severidad: MEDIA  
Ãrea: mÃ³dulos tenant

### Problema

Solo algunos mÃ³dulos tienen README completo. Otros dependen del cÃ³digo.

### RecomendaciÃ³n

Crear README mÃ­nimo para:

- `pos`
- `importador`
- `productions`
- `accounting`
- `billing`
- `settings`
- `webhooks`
- `templates`
- `reports`

Prioridad alta:

1. POS
2. Importador
3. ProducciÃ³n
4. Billing/e-invoicing
5. Settings

### Resultado revisado

- Todos los mÃ³dulos tenant tienen README mÃ­nimo con estado, madurez, riesgo, implementado, parcial, pendiente, endpoints, permisos y tests mÃ­nimos.

---

## F-12 â€” Falta matriz de permisos frontend por mÃ³dulo

Estado: HECHO 2026-06-13  
Severidad: ALTA  
Ãrea: mÃ³dulos tenant, roles, settings

### Problema

Los mÃ³dulos usan permisos, pero no hay una tabla Ãºnica de permisos esperados.

### RecomendaciÃ³n

Crear:

```text
docs/frontend-permissions-matrix.md
```

Ejemplo:

| MÃ³dulo | Read | Create | Update | Delete | Especiales |
|---|---|---|---|---|---|
| users | users:read | users:create | users:update | users:delete | roles:* |
| pos | pos:read | pos:create | pos:update | pos:delete | pos:close_shift, pos:refund |
| importador | imports:read | imports:create | imports:update | imports:delete | imports:confirm, imports:route |
| settings | settings:read | - | settings:update | - | settings:billing, settings:security |

### Resultado revisado

- Existe `docs/frontend-permissions-matrix.md`.
- La matriz contrasta protecciÃ³n frontend y backend observado, e identifica gaps prioritarios.

---

## F-13 â€” Falta error boundary por mÃ³dulo

Estado: HECHO 2026-06-13  
Severidad: MEDIA  
Ãrea: ModuleLoader, mÃ³dulos complejos

### Problema

Si un mÃ³dulo rompe en render, puede tirar toda la app tenant.

### RecomendaciÃ³n

AÃ±adir `ModuleErrorBoundary`:

```tsx
<ModuleErrorBoundary module={canonicalModule}>
  <Component />
</ModuleErrorBoundary>
```

Debe mostrar:

- mÃ³dulo afectado,
- botÃ³n recargar,
- botÃ³n volver al dashboard,
- cÃ³digo de error en modo dev,
- log hacia telemetry si existe.

### Resultado aplicado

- AÃ±adido `ModuleErrorBoundary` en `apps/tenant/src/components/ModuleErrorBoundary.tsx`.
- `ModuleLoader` envuelve cada mÃ³dulo dinÃ¡mico con el boundary.
- El fallback muestra mÃ³dulo afectado, permite recargar y volver al dashboard.
- Pendiente futuro: conectar telemetry real si se define una capa de observabilidad frontend.

---

## F-14 â€” Falta estado de madurez por mÃ³dulo en UI/Admin

Estado: HECHO 2026-06-13  
Severidad: MEDIA  
Ãrea: Admin modules, Tenant modules

### Problema

Todos los mÃ³dulos pueden parecer igual de listos cuando no lo estÃ¡n.

### RecomendaciÃ³n

AÃ±adir metadatos:

```ts
status: 'stable' | 'beta' | 'experimental' | 'legacy'
risk: 'low' | 'medium' | 'high'
requiresOfflineAudit?: boolean
requiresFiscalValidation?: boolean
```

Y usarlos en Admin para no vender/activar accidentalmente mÃ³dulos verdes.

### Resultado revisado

- Todos los `module.json` tenant tienen `status`, `maturity` y `risk`.
- La UI de mÃ³dulos muestra estado, madurez, riesgo y flags de auditorÃ­a si la API entrega esos campos.

---

## F-15 â€” Falta E2E real por mÃ³dulo crÃ­tico

Estado: HECHO INICIAL 2026-06-13  
Severidad: ALTA  
Ãrea: CI/frontend

### Problema

Hay Vitest y Testing Library, pero un SaaS de este tipo necesita E2E.

### RecomendaciÃ³n

AÃ±adir Playwright:

```text
apps/tenant/e2e/
  auth.spec.ts
  modules.spec.ts
  pos.spec.ts
  importador.spec.ts
  production.spec.ts
  billing.spec.ts
```

Smoke mÃ­nimo obligatorio:

```text
1. Login tenant
2. Carga dashboard
3. MÃ³dulo permitido abre
4. MÃ³dulo no permitido redirige unauthorized
5. Refresh mantiene sesiÃ³n
6. Logout borra sesiÃ³n
```

### Resultado revisado

- Existe suite Playwright en raÃ­z `e2e/` y script `npm run test:e2e`.
- Hay specs para auth, smoke, navegaciÃ³n, POS, inventario, facturaciÃ³n, producciÃ³n, reportes, notificaciones, reconciliaciÃ³n y webhooks.
- Se aÃ±adieron `e2e/importador.spec.ts` y `e2e/permissions.spec.ts`.
- Queda deuda QA: ejecutar contra entorno con fixtures y endurecer asserts de permisos/refresh/logout.

---

## 4. Ranking de mÃ³dulos Tenant

| MÃ³dulo | Nota | Estado |
|---|---:|---|
| POS | 7.5/10 | Muy avanzado, alto riesgo |
| Importador | 7/10 funcional / 5/10 seguridad | Potente, crÃ­tico |
| ProducciÃ³n | 7/10 | Muy Ãºtil para panaderÃ­a |
| Settings | 7/10 | Bastante trabajado |
| Users/Roles | 7/10 | Correcto y protegido |
| Productos | 7/10 | Bien documentado |
| Inventario | 7/10 | Bien planteado |
| Contabilidad | 6.8/10 | Amplio, validar cÃ¡lculos |
| Ventas | 6.5/10 | CRUD correcto |
| Billing/Invoicing | 6.3/10 | Necesita mÃ¡s validaciÃ³n fiscal |
| Reports | 6/10 | Ãštil, validar fuentes/cÃ¡lculos |
| Customers | 6/10 | CRUD correcto |
| Suppliers | 6/10 | CRUD correcto |
| Purchases | 6/10 | Correcto, rutas en inglÃ©s |
| Expenses | 6/10 | Correcto |
| Webhooks | 4.8/10 | Muy bÃ¡sico, falta protecciÃ³n explÃ­cita |
| Templates | 4.8/10 | Muy bÃ¡sico, falta protecciÃ³n explÃ­cita |

---

## 5. Orden recomendado de trabajo

## Fase 1 â€” Seguridad y consistencia

1. Auditar `offlineAuth`.
2. AÃ±adir protecciÃ³n explÃ­cita a `webhooks`, `templates`, `notifications`.
3. Unificar rutas `nuevo/editar` vs `new/edit`.
4. Eliminar `any` de `ProtectedRoute`.
5. Documentar matriz de permisos.

## Fase 2 â€” HTTP/Auth compartido

6. Definir cliente HTTP Ãºnico.
7. Migrar servicios legacy a `tenantApi` o cliente estÃ¡ndar.
8. Centralizar tratamiento de errores.
9. Centralizar refresh/CSRF.
10. Prohibir fetch directo salvo excepciÃ³n.

## Fase 3 â€” MÃ³dulos crÃ­ticos

11. POS: idempotencia, E2E, offline sync, caja.
12. Importador: confirmaciÃ³n, trazabilidad, raw AI JSON, destinos.
13. ProducciÃ³n: costes, recetas, planificaciÃ³n, integraciÃ³n stock.
14. Billing/e-invoicing: validaciones fiscales y estados.
15. Reports: validar cÃ¡lculos contra backend.

## Fase 4 â€” DocumentaciÃ³n y DX

16. Actualizar `docs/frontend-commands.md`.
17. Crear README estÃ¡ndar por mÃ³dulo.
18. Crear `docs/frontend-modules-status.md`.
19. Formalizar `apps/packages`.
20. AÃ±adir Playwright smoke tests.

---

## 6. Backlog accionable

| ID | Mejora | Prioridad | MÃ³dulos |
|---|---|---:|---|
| FE-001 | Auditar offline auth | Alta | Tenant/Auth/POS |
| FE-002 | Unificar HTTP clients | Alta | Todos |
| FE-003 | Proteger webhooks/templates | Alta | Webhooks/Templates |
| FE-004 | Crear matriz permisos frontend | Alta | Todos |
| FE-005 | E2E login + mÃ³dulos | Alta | Tenant |
| FE-006 | E2E POS offline/sync | Alta | POS |
| FE-007 | E2E importador confirmaciÃ³n | Alta | Importador |
| FE-008 | Normalizar rutas idioma | Media | Purchases/Expenses/etc |
| FE-009 | Eliminar `any` en auth/routes | Media | Auth/Shared UI |
| FE-010 | Error boundary por mÃ³dulo | Media | ModuleLoader |
| FE-011 | README estÃ¡ndar por mÃ³dulo | Media | Todos |
| FE-012 | Formalizar packages | Media | apps/packages |
| FE-013 | Marcar mÃ³dulos beta/stable | Media | Admin/Tenant |
| FE-014 | Limpiar docs infladas | Media | Docs mÃ³dulos |
| FE-015 | Validar cÃ¡lculos reports | Media | Reports/Accounting |

---

## 7. DefiniciÃ³n de â€œfrontend proâ€ para GestiQCloud

Para considerar el frontend listo para vender de forma seria:

- `npm run check` pasa siempre en Admin y Tenant.
- Hay Playwright smoke para login, mÃ³dulo permitido y mÃ³dulo denegado.
- POS tiene pruebas de caja, ticket, pago y sync offline.
- Importador obliga confirmaciÃ³n humana antes de guardar destinos crÃ­ticos.
- Todos los mÃ³dulos tienen `ProtectedRoute` interno.
- No hay `any` en auth, permisos o clientes HTTP.
- Rutas estÃ¡n normalizadas.
- `apps/packages` tiene README y ownership claro.
- Cada mÃ³dulo tiene estado: stable/beta/experimental.
- La documentaciÃ³n separa implementado, parcial y pendiente.

---

## 8. Veredicto final

El frontend de GestiQCloud no es humo. Hay una base seria, especialmente en Tenant: mÃ³dulos dinÃ¡micos, permisos, PWA, POS, importador y producciÃ³n.

Pero ahora mismo estÃ¡ en un punto mixto: partes muy avanzadas conviven con mÃ³dulos simples, documentaciÃ³n optimista y zonas sensibles sin suficiente blindaje.

La prioridad no deberÃ­a ser aÃ±adir mÃ¡s pantallas. La prioridad deberÃ­a ser endurecer lo que ya existe:

1. Auth/offline.
2. POS.
3. Importador.
4. Permisos.
5. HTTP compartido.
6. Tests E2E.
7. DocumentaciÃ³n realista.

Con esas mejoras, el frontend puede pasar de â€œbuen prototipo SaaS avanzadoâ€ a â€œproducto SaaS mantenible y vendibleâ€.
