# Módulo: identity

Autenticación (admin y tenant), rotación de refresh tokens y sesión/cookies. No cubre gestión de usuarios (se hace en `users`) ni permisos/roles más allá de los claims emitidos.

## Alcance y límites
- Cubre: login, refresh, logout, bootstrap CSRF, set-password por token de email, rotación de familia de refresh, guardado de sesión y claims (tenant_id/user_id/is_company_admin).
- No cubre: recuperación de contraseña vía email (solo set-password con token ya emitido), MFA, gestión de roles, impersonación.

## Endpoints principales
- `POST /api/v1/tenant/auth/login` — Body `{ identificador, password }` (email o username). Devuelve `access_token`, `token_type`, `scope`, `tenant_id`, flags de empresa y setea cookies `access_token` (Lax) y `refresh_token` (HttpOnly, path `/tenant/auth/refresh`). Rate-limit por IP+identificador (429 con `Retry-After`).
- `POST /api/v1/tenant/auth/refresh` — Usa cookie `refresh_token`; rota la familia (`auth_refresh_*`), devuelve nuevo access/refresh y renueva cookies. Rechaza reuse (401) y marca familia revocada.
- `POST /api/v1/tenant/auth/logout` — Best-effort revoca familia (si cookie presente) y borra cookies. Idempotente.
- `GET /api/v1/tenant/auth/csrf` — Devuelve `{ ok, csrfToken }` y setea cookie legible `csrf_token`.
- `POST /api/v1/tenant/auth/set-password` — Body `{ token, password }` (token email emitido fuera del módulo). Valida longitud >=8, 404 si usuario no existe.
- Admin (prefijo `/api/v1/admin/auth/*`): mismos flujos login/refresh/logout/csrf pero con `SuperUser`, `ADMIN_SYSTEM_TENANT_ID` y path de cookie `/admin/auth/refresh`.

### Ejemplos
```
POST /api/v1/tenant/auth/login
{ "identificador": "user@acme.com", "password": "hunter2" }
→ 200 { "access_token": "...", "token_type": "bearer", "scope": "tenant", "tenant_id": "<uuid>", "empresa_slug": "acme", "is_company_admin": true }

POST /api/v1/tenant/auth/refresh
Cookie: refresh_token=<jwt>
→ 200 { "access_token": "...", "expires_in": 3600 }
```

### Errores comunes
- `400 invalid_request|weak_password` (set-password), `401 invalid_credentials`, `401 tenant_id inválido` si falta claim, `429 too_many_attempts`, `500 refresh_family_error|claims_error`.

## Modelos/DB y migraciones
- Tablas `auth_refresh_family`, `auth_refresh_token` (creadas en `001_initial_schema` vía metadata); guardan familia y tokens con hashes de UA/IP.
- Usuarios: `company_user` (tenant) y `auth_super_user` (admin) creados también en `001_initial_schema`.
- No hay migraciones específicas posteriores; revisar `alembic/versions/005_pos_extensions.py` y siguientes para cambios generales si se añaden campos.

## Flujos críticos
- Login tenant: valida rate limit → busca usuario por email/username → verifica hash (rehash si es necesario) → session scope `tenant_id` → emite claims con `build_tenant_claims` (puede fallar si la transacción aborta) → crea familia refresh → emite JWTs → setea cookies.
- Refresh: rota refresh (marca `used_at`, valida reuse, revoca familia si reuse) y emite nuevo par; si reuse detectado devuelve 401 y fuerza relogin.
- Logout: best-effort revoca familia; siempre borra cookies aunque la revocación falle.
- Cookies: `set_access_cookie` (Lax), `set_refresh_cookie` (HttpOnly, SameSite según entorno) con paths específicos para admin/tenant. Worker CF puede reescribir dominio/SameSite.

## Dependencias y env vars
- `SECRET_KEY`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`, expiraciones, `ADMIN_SYSTEM_TENANT_ID`.
- Bases de datos para tablas auth, audit y usuarios (`DATABASE_URL`).
- Entornos: ver `docs/entornos.md` para dominios/flags (RLS, OTEL). En prod se sirve detrás de Cloudflare Worker.

## Casos de uso principales
- Login/refresh admin (panel) y tenant (app) con cookies seguras.
- Set-password por token de email (workflow de onboarding/recuperación).
- Bootstrap CSRF para formularios en admin/tenant.
- Revocación de familia al cerrar sesión o detectar reuse.

## Pruebas mínimas
- Feliz: login tenant con usuario válido → cookies y `access_token` presentes; refresh devuelve nuevo token y mantiene sesión; logout borra cookies.
- Validación: login con password incorrecta devuelve 401 y aumenta rate-limit; set-password con token inválido 400, password <8 400.
- Auth/tenancy: login tenant sin `tenant_id` o usuario sin tenant devuelve 401; admin login no setea tenant claims pero fija `ADMIN_SYSTEM_TENANT_ID` en GUC.
- Estados límite: reuse de refresh devuelve 401 y marca familia revocada; retry after en rate-limit incluye header.
- Idempotencia: logout repetido responde `{ok: true}` sin error.
- Reintentos externos: verificar CSRF entrega token y cookie legible.

## Consumidores y compatibilidad
- Front tenant (`apps/tenant`) y admin (`apps/admin`) consumen login/refresh/csrf/logout.
- Cambios de schema en tokens/claims son breaking; introducir claims nuevos como opcionales y documentar en `docs/api-contracts.md` y `apps/packages/api-types/identity.ts`.
