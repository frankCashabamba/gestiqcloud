# Seguridad

## Manejo de secretos
- Usar variables de entorno (`.env` no se commitea). Claves sensibles: `SECRET_KEY`, `JWT_SECRET_KEY`, credenciales DB, proveedores de pago.
- En producción, configurar secretos en Render/Cloudflare; no en repositorio.

## Autenticación y cookies
- Auth por cookies HttpOnly (`access_token` SameSite=Lax, `refresh_token` SameSite=None; Secure). Dominio `.gestiqcloud.com` reescrito en el worker.
- Login: `/api/v1/tenant/auth/login`, `/api/v1/admin/auth/login`. Refresh y password reset siguen mismos dominios.

## Autorización y roles
- Permisos cargados desde configuraciones de módulos/roles (ver `app/core/permissions.py`).
- Rate limiting global y por endpoint crítico (login/password) activo por defecto (`RATE_LIMIT_ENABLED`, `ENDPOINT_RATE_LIMIT_ENABLED`).

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
- El esquema consolidado soporta `tenant_id`; activar RLS en Postgres por tabla de negocio con `ALTER TABLE ... ENABLE ROW LEVEL SECURITY;`.
- Añadir políticas por tenant: `CREATE POLICY tenant_isolation ON <tabla> USING (tenant_id = current_setting('app.current_tenant')::uuid);`.
- Ajustar la sesión para establecer `app.current_tenant` al inicio de cada request (en pool/connection) si se habilita RLS.
- Probar consultas críticas tras activar RLS; incluir en suite de smoke tests.
- Para producción, planificar activación gradual: primero habilitar RLS en tablas de baja criticidad, monitorear, luego extender al resto.
- Comandos base:
  ```sql
  ALTER TABLE ventas ENABLE ROW LEVEL SECURITY;
  CREATE POLICY tenant_isolation ON ventas
    USING (tenant_id = current_setting('app.current_tenant')::uuid);
  ```
- Flujo operativo recomendado:
  1) Preparar migración Alembic o SQL con `ENABLE RLS` + políticas.
  2) Asegurar que la sesión establece `app.current_tenant` al abrir conexión (middleware DB).
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
