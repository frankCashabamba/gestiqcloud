# Admin (React/Vite)

Panel de administración para configurar tenants, módulos y plantillas.

## Cómo correr
```bash
cd apps/admin
npm install
npm run dev -- --host --port 8081
```

## Build y test
```bash
npm run typecheck
npm run build
```

## Env vars (Vite)
- `VITE_API_URL`: base del backend.
- `VITE_BASE_PATH`: base de la app (normalmente `/`).
- `VITE_TENANT_ORIGIN`: origen del tenant (para CORS/redirecciones).
- `VITE_ADMIN_ORIGIN`: origen del admin.

## Rutas/módulos principales
- Empresas (listar/crear/editar, módulos asignados, roles).
- Configuración global: sectores, tipos de negocio/empresa, idiomas, países, monedas, timezones, plantillas UI.
- Logs/Incidencias, Migraciones (pantallas internas).
- Usuarios admin/tenant.

## Autenticación y flujo
- Login en `/api/v1/admin/auth/login` (cookies HttpOnly gestionadas por backend/worker).
- Guardas: `AuthContext` + rutas protegidas (permisos por rol).
- Para apuntar a otra API, ajustar `VITE_API_URL` y orígenes; limpiar caché del navegador si hay cookies previas.

## Rutas/páginas principales
- Login, panel de empresas, configuración (sectores, módulos, idiomas, países, timezones), incidencias/logs, migraciones.

## Uso de paquetes compartidos
- UI y lógica desde `apps/packages/*` (ui, utils, endpoints, auth-core, http-core, api-types).

## Troubleshooting
- Si `npm ci` falla en CI por lock mismatch, CI ya hace fallback a `npm install`.
- Problemas de CORS/cookies: verificar que `VITE_API_URL` apunte al dominio correcto (worker aplica CORS).

## Pendientes
- Añadir guía de testing manual y mocks de API.
