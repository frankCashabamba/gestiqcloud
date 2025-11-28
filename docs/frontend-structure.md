# Estructura frontends (Admin, Tenant, Packages)

## apps/admin (React/Vite)
- `src/` principal:
  - `pages/`: rutas (Login, AdminPanel, Empresas, Configuración, Logs, Incidencias, etc.).
  - `features/`: módulos de negocio (configuración de sector/idiomas/horarios, modulos, etc.).
  - `components/`: UI reusable (cards, charts, modales, etc.).
  - `hooks/`: hooks de negocio (useEmpresas, useAuthGuard, etc.).
  - `services/`: clientes HTTP por recurso (usuarios, empresas, logs, incidents, modulos, etc.).
  - `lib/`: utilidades comunes (api/http/telemetry).
  - `auth/`: AuthContext y guardas.
  - `style/`: layout/temas.
- `public/`: estáticos y SW.
- Config: `vite.config.ts`, `tsconfig*.json`, env Vite (`VITE_*`).

## apps/tenant (React/Vite, PWA)
- `src/app/`: shell, rutas, guardas.
- `src/modules/`: módulos de negocio (clientes, finanzas, contabilidad, facturación, importador, etc.) cada uno con `manifest`, `Routes`, `services`, `components`, README si aplica.
- `src/auth/`: AuthContext.
- `src/shared/`: UI/utilidades compartidas (toast, pagination, etc.).
- `src/lib/`: http, telemetry, electric.
- `src/sw.js`: Service Worker y PWA helpers; `public/offline.html`.
- Config: `vite.config.ts`, `tailwind.config.cjs`, `vitest.config.ts`, env Vite (`VITE_*`).

## apps/packages (monorepo de librerías TS)
- Paquetes principales:
  - `ui`: componentes React (guardas, banners offline, etc.) y preset Tailwind.
  - `auth-core`: helpers de auth/sesión.
  - `http-core`: cliente HTTP.
  - `endpoints`: definiciones de endpoints admin/tenant.
  - `api-types`: tipos/contratos de API.
  - `utils`: utilidades (permisos, formularios).
  - `shared`: telemetry/outbox helpers.
  - `pwa`: plugin/configuración PWA.
- `telemetry`: capa de telemetría.
- `domain`: lógica de dominio compartida (onboarding/empresa, etc.).
- `assets`, `zod`: assets y esquemas.
- Cada paquete tiene su `package.json`/lock y src propio.

## Enlaces útiles
- Guías específicas: `apps/admin/README.md`, `apps/tenant/README.md`, `apps/packages/README.md`.
- Ejemplos HTTP: `docs/examples-curl.md`.

## Contratos y versionado
- `apps/packages/api-types` y `apps/packages/endpoints` son la fuente de verdad para contratos consumidos en front; sincronizar cambios con `docs/api-contracts.md`.
- Para cambios de backend: publicar primero types/endpoints, actualizar servicios en admin/tenant, y solo luego limpiar código antiguo.
- Definir `VITE_API_BASE_URL`/`VITE_ADMIN_API_BASE_URL` por entorno; evitar hardcode de dominios.
- Mantener mocks/fixtures en cada módulo para pruebas y storybook si aplica.

## Flujo de desarrollo sugerido
- Crear feature branch que toque backend + packages + front; versionar paquetes si se publican.
- Añadir pruebas (unit/vitest) por módulo afectado y smoke E2E manual con `npm run dev` en admin/tenant.
- Revisar PWA/service worker al cambiar rutas públicas; validar cache busting.
