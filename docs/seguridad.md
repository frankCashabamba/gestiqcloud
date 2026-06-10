# Seguridad

## Manejo de secretos
- Usar variables de entorno (`.env` no se commitea). Claves sensibles: `SECRET_KEY`, `JWT_SECRET_KEY`, credenciales DB, proveedores de pago.
- En producción, configurar secretos en Render/Cloudflare; no en repositorio.

## Autenticación y cookies
- Auth por cookies HttpOnly (`access_token` SameSite=Lax, `refresh_token` SameSite=None; Secure). Dominio `.gestiqcloud.com` reescrito en el worker.
- Login: `/api/v1/tenant/auth/login`, `/api/v1/admin/auth/login`. Refresh y password reset siguen mismos dominios.

## CSRF
- Protegido por `RequireCSRFMiddleware` (`app/middleware/require_csrf.py`), montado en `app/main.py` bajo el flag `CSRF_ENABLED` (default on). Se registra antes que `SessionMiddleware` para ver `request.state.session`.
- Esquema double-submit: el frontend pide el token vía `GET /api/v1/{tenant|admin}/auth/csrf` (emite cookie `csrf_token`, `httponly=False`, `samesite=lax`) y lo reenvía en el header `X-CSRF-Token` (o `X-CSRF`). El middleware valida header == cookie o header == `session["csrf"]`.
- **Exentos**: métodos seguros (GET/HEAD/OPTIONS); `/auth/login`, `/auth/refresh`, `/auth/logout`; webhooks entrantes externos por segmento `/webhook/` (Telegram, Stripe `/tenant/billing/webhook/stripe`, pasarelas `/reconciliation/webhook/{provider}`). Los `/webhooks/` (plural, gestión del tenant) **sí** exigen CSRF.
- Tras Cloudflare Worker: verificar que el header `X-CSRF-Token` no se elimine en el proxy `/api/*`.
- Bajo pytest el middleware hace bypass (igual que `with_access_claims`); los tests específicos de CSRF lo fuerzan con `PYTEST_DISABLE_CSRF_BYPASS=1`.

## Autorización y roles
- Permisos cargados desde configuraciones de módulos/roles (ver `app/core/permissions.py`).
- Guards: `require_scope("admin"|"tenant")` (por `kind` del token) y `require_permission(...)` (`app/core/authz.py`). Ojo: `require_permission` hace bypass para `is_company_admin`; para endpoints de **plataforma** (p.ej. auditoría global en `routers/admin_logs.py` `/audit`, `/audit/stats`) usar `require_scope("admin")`, que rechaza tokens `kind="tenant"`.
- Bypass RLS: inventariado en `docs/security/bypass-rls-register.md`. Ningún bypass sin motivo, condición, test cross-tenant, owner y fecha.
- Rate limiting global y por endpoint crítico (login/password) activo por defecto (`RATE_LIMIT_ENABLED`, `ENDPOINT_RATE_LIMIT_ENABLED`).

## Rate limiting (capas)
Tres capas con responsabilidad distinta (todas con storage Redis cuando hay `REDIS_URL`):
- **`RateLimitMiddleware`** (`middleware/rate_limit.py`): límite **global** de tráfico por user/tenant/IP (Redis; fail-open sin Redis).
- **`EndpointRateLimiter`** (`middleware/endpoint_rate_limit.py`): límites **por endpoint crítico** (login, password-reset, admin/users…) declarados como `{ruta: (max, ventana_s)}`. Usa **Redis** (fixed-window) con **fallback a memoria**. En producción multi-proceso Redis es imprescindible: con memoria local el límite se evade repartiendo requests entre procesos.
- **`SimpleRateLimiter` / `core/login_rate_limit`**: **lockout anti-fuerza-bruta** por *fallos* de login (Redis). Cuenta fallos, no requests; complementa al `EndpointRateLimiter`.
- El antiguo decorador `rate_limit()` (memoria local, sin uso) fue **eliminado**.

## Dependencias y actualizaciones
- CI usa Python 3.11 y Node 20; mantener locks (`requirements*.txt`, `package-lock.json`) actualizados.
- Revisar vulnerabilidades en npm/pip antes de releases.

## Rotación de claves
- `SECRET_KEY` (cookies/sesiones) y `JWT_SECRET_KEY` (tokens) deben rotarse periódicamente en producción y almacenarse solo como secretos gestionados (Render/Cloudflare).
- Estrategia sugerida JWT: admitir claves públicas adicionales (`JWT_ADDITIONAL_PUBLIC_KEYS`) para periodo de gracia y luego retirar la antigua.
- Documentar fecha de rotación y responsables; nunca commitear claves en el repo.
- Procedimiento (prod):
  1) Generar nueva clave segura y cargarla como secreto (sin reiniciar todavía).
  2) Añadir `JWT_ADDITIONAL_PUBLIC_KEYS` con la clave pública saliente (si usas RSA/ES) para permitir verificación durante la transición.
  3) Desplegar backend con la nueva clave activa; monitorear errores de login/refresh.
  4) Pasado el periodo de gracia, retirar la clave antigua de `JWT_ADDITIONAL_PUBLIC_KEYS`.
  5) Registrar la rotación (fecha, responsable, impacto) y validar smoke tests de auth.

## RLS (Row-Level Security)
> 🔴 **CRÍTICO (2026-06-10): la app NO debe conectarse como superuser.** Postgres ignora RLS para superusers, incluso con `FORCE ROW LEVEL SECURITY`. Verificado: conectando como `postgres` (superuser), `tenant_session_scope(A)` veía datos de todos los tenants; con un rol no-superuser aísla correctamente. **`DATABASE_URL` (backend y workers) debe usar un rol de aplicación NO-superuser** con grants mínimos. Test invariante: `test_app_db_connection_is_not_superuser`. Pendiente además: `FORCE ROW LEVEL SECURITY` en las 15 tablas RLS que aún no lo tienen.

> **Nombre del GUC (verificado contra código 2026-06-09):** la sesión del backend setea `app.tenant_id`, `app.user_id` y `app.bypass_rls` (ver `app/config/database.py`, hook `after_begin`). Las políticas RLS deben usar **`app.tenant_id`**, no `app.current_tenant`. `app/db/session.py` es ahora un shim de `app/config/database.py` (C-01 resuelto).
- El esquema consolidado soporta `tenant_id`; activar RLS en Postgres por tabla de negocio con `ALTER TABLE ... ENABLE ROW LEVEL SECURITY;`.
- Añadir políticas por tenant: `CREATE POLICY tenant_isolation ON <tabla> USING (tenant_id = current_setting('app.tenant_id')::uuid);`.
- La sesión principal ya establece `app.tenant_id` al inicio de cada transacción (`after_begin`); los workers deben usar un helper que haga lo mismo en vez de abrir sesiones crudas.
- Probar consultas críticas tras activar RLS; incluir en suite de smoke tests.
- Para producción, planificar activación gradual: primero habilitar RLS en tablas de baja criticidad, monitorear, luego extender al resto.
- Comandos base:
  ```sql
  ALTER TABLE ventas ENABLE ROW LEVEL SECURITY;
  CREATE POLICY tenant_isolation ON ventas
    USING (tenant_id = current_setting('app.tenant_id')::uuid);
  ```
- Flujo operativo recomendado:
  1) Prepare an SQL migration with `ENABLE RLS` and the required policies.
  2) Asegurar que la sesión establece `app.tenant_id` al abrir conexión (middleware DB).
  3) Habilitar en staging y correr smoke tests (listados, inserts, updates) por tenant.
  4) Activar en producción por lotes y monitorear errores 403/500 en logs.
  5) Añadir pruebas automatizadas de RLS en CI si se fija el tenant en las sesiones de test.

## Checklists cambios sensibles
- Cambios en auth/cookies: validar CORS y SameSite en worker + navegador.
- Cambios en pagos/e-invoicing: probar entorno sandbox de cada proveedor.
- Migraciones destructivas: backup previo (`pg_dump`) y plan de rollback.

## Pendientes
- Añadir procedimiento operativo estándar para rotación (cronograma y verificación).
- Documentar secuencia de activación RLS con migraciones y smoke tests automatizados.
