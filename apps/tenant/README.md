# Tenant PWA (React/Vite)

Aplicación PWA para usuarios de cada empresa (tenant), con soporte offline y módulos configurables.

## Cómo correr
```bash
cd apps/tenant
npm install
npm run dev -- --host --port 8082
```

## Build y test
```bash
npm run typecheck
npm run build
npm run test        # Vitest si se habilita
```

## Env vars (Vite)
- `VITE_API_URL`: base del backend.
- `VITE_BASE_PATH`: base de la app (ej. `/`).
- `VITE_TENANT_ORIGIN`, `VITE_ADMIN_ORIGIN`: orígenes permitidos (CORS/cookies).

## Rutas/módulos principales
- Clientes/CRM, compras, gastos, finanzas/caja/bancos, facturación/e-invoicing, contabilidad, importador, dashboards por sector.
- Cada módulo tiene `manifest`, `Routes`, `services` y a veces README (ej. `src/modules/clientes/README.md`).

## Autenticación y flujo
- Login contra `/api/v1/tenant/auth/login` (cookies HttpOnly gestionadas por backend/worker).
- `AuthContext` gestiona sesión y refresh; rutas protegidas con `ProtectedRoute`.
- Para apuntar a otra API, cambia `VITE_API_URL` y los orígenes; limpiar SW para evitar caché.

## Módulos principales
- CRM/clientes, compras, gastos, finanzas/caja/bancos, facturación/e-invoicing, contabilidad, importador, dashboards sector.
- Ejemplo de doc de módulo: `src/modules/clientes/README.md` (campos configurables por tenant/sector).

## PWA/offline y caché
- Service Worker en `src/sw.js`. Para ver cambios recientes, forzar recarga dura o limpiar SW.
- `public/offline.html` como fallback; componentes de UI muestran banners si offline.
- Cache bust: al cambiar `VITE_BASE_PATH` o assets, limpiar SW manualmente (Ctrl+F5 o desde DevTools) o esperar prompt de actualización.
- Requests: cliente HTTP respeta cookies; invalidaciones de caché dependen del SW y de headers del backend.
- Estrategia de SW: precache básico + fetch con fallback; al cambiar endpoints/basepath, limpiar SW para evitar respuestas stale.

## Uso de paquetes compartidos
- Reutiliza `apps/packages` (ui, endpoints, utils, pwa, telemetry, api-types, shared).

## Troubleshooting
- CORS/cookies: validar `VITE_API_URL` y dominios; worker reescribe cookies para dominios finales.
- Cacheo agresivo: limpiar SW si la UI no refleja builds nuevas.

## Pendientes
- Añadir ejemplos de rutas y flujo de auth en la app.
- Documentar procesos del importador (ver `src/modules/importador/FRONTEND_TODO.md`).
