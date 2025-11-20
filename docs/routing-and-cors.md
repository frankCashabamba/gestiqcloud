GestiQCloud — Routing & CORS (v1)

Resumen
- Edge Gateway (Cloudflare Worker) expone únicamente rutas públicas bajo `https://api.gestiqcloud.com/v1/*` y `GET /health|/ready`.
- El backend FastAPI escucha en Render en `/api/v1/*` (no público).
- El Worker reescribe `GET/POST ... /v1/*` → upstream `/api/v1/*` y aplica CORS/seguridad.
- Frontends (Admin/Tenant) consumen `https://api.gestiqcloud.com` + rutas `/v1/...`.

Dominios
- API pública: `https://api.gestiqcloud.com`
- Admin FE: `https://admin.gestiqcloud.com`
- Tenant FE: `https://gestiqcloud.com` (o `https://www.gestiqcloud.com`)

Estándar de rutas
- Siempre prefijo `/v1` para llamadas desde el navegador.
- Ejemplos:
  - Admin auth: `/v1/admin/auth/login|refresh|logout|csrf`
  - Tenant auth: `/v1/auth/login|refresh|logout|csrf`
  - Health: `/health`, `/ready` (solo GET)

Config FE
- Admin (`apps/admin/.env.production`)
  - `VITE_API_URL=https://api.gestiqcloud.com`
  - `VITE_TENANT_ORIGIN=https://gestiqcloud.com`
  - `VITE_ADMIN_ORIGIN=https://admin.gestiqcloud.com`
- Tenant (Dockerfile genera `.env.production`)
  - `VITE_API_URL=https://api.gestiqcloud.com`
  - `VITE_TENANT_ORIGIN=https://gestiqcloud.com`
  - `VITE_ADMIN_ORIGIN=https://admin.gestiqcloud.com`

Gateway (Worker)
- Acepta orígenes (`ALLOWED_ORIGINS`) y refleja CORS con `Allow-Credentials: true`.
- Reescrituras:
  - api.gestiqcloud.com: `/v1/*` → `/api/v1/*`; `/health|/ready` → 200.
  - admin/www: igual; bloquea rutas `/api/*` públicas.
- Cookies endurecidas:
  - `access_token`: `SameSite=Lax`, `Secure`, `HttpOnly`, `Domain=.gestiqcloud.com`, `Path=/`.
  - `refresh_token`: `SameSite=None`, `Secure`, `HttpOnly`, `Domain=.gestiqcloud.com`, `Path=/`.
- Errores con CORS: 404/403 devuelven CORS correcto (parches aplicados).

Backend (FastAPI)
- Mantener `CORS_ORIGINS` con `https://admin.gestiqcloud.com,https://www.gestiqcloud.com` en producción.
- `allow_credentials=True`, `allow_methods=['GET','POST','PUT','PATCH','DELETE','OPTIONS']`.

Wrangler (workers/wrangler.toml)
- `ALLOWED_ORIGINS="https://admin.gestiqcloud.com,https://www.gestiqcloud.com"`.
- `COOKIE_DOMAIN=.gestiqcloud.com`.
- `TARGET` debe apuntar al Render del backend.

Checklist de verificación
1) Preflight (desde Admin origin)
   curl -i \
     -H "Origin: https://admin.gestiqcloud.com" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: content-type" \
     -X OPTIONS https://api.gestiqcloud.com/v1/admin/auth/refresh
   - Esperado: 204 con `Access-Control-Allow-Origin: https://admin.gestiqcloud.com` y `Allow-Credentials: true`.

2) Refresh
   curl -i -X POST https://api.gestiqcloud.com/v1/admin/auth/refresh \
     -H "Origin: https://admin.gestiqcloud.com" \
     --cookie "refresh_token=..." --cookie "csrf_token=..."
   - Esperado: 200 con CORS y `Set-Cookie: access_token=...` (Lax) reescrito por el gateway.

3) Logout
   curl -i -X POST https://api.gestiqcloud.com/v1/admin/auth/logout \
     -H "Origin: https://admin.gestiqcloud.com"
   - Esperado: 200/204 con CORS.

4) 404 y 403 con CORS
   curl -i -H "Origin: https://admin.gestiqcloud.com" https://api.gestiqcloud.com/v1/no-existe
   - Esperado: 404 con `Access-Control-Allow-Origin` correcto.

5) Tenant FE
   - BaseURL `/v1`, endpoints TENANT_AUTH.
   - En navegador, `fetch('https://api.gestiqcloud.com/v1/auth/csrf', { credentials: 'include' })` devuelve 200 y cookie CSRF.

Operación
- Desplegar Worker: `wrangler publish` (verificar bindings/vars).
- Desplegar Admin/Tenant: asegurar `.env.production` válidos (admin usa el repo, tenant lo escribe el Dockerfile).
- Backend Render: setear `CORS_ORIGINS` y `ALLOWED_HOSTS` con dominios públicos.

Notas
- Evitar base `/api` en FE: siempre `https://api.gestiqcloud.com` + `/v1/...`.
- El Worker bloquea `/api/*` público a propósito para minimizar superficie.
