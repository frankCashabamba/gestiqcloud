# Rol de base de datos de la aplicación (no-superuser)

> **Por qué:** la app se conecta como `postgres` (superuser). Postgres **ignora RLS
> para superusers**, así que el aislamiento por tenant no está protegido por RLS
> (solo por los filtros `WHERE` del código). La solución es que la app use un rol
> limitado. Hallazgo del 2026-06-10 — ver auditoría §0.0 y `docs/seguridad.md`.

## Qué se aplica

- `ops/security/01_create_app_role.sql` → crea el rol `gestiq_app` (LOGIN, **NO** superuser, **NO** bypass RLS) y le da los permisos mínimos (CRUD en tablas, uso de secuencias, ejecutar funciones), incluido para objetos futuros.
- `ops/security/02_force_rls_remaining.sql` → `FORCE ROW LEVEL SECURITY` en 15 tablas que faltaban (hardening; lo esencial es el rol).

## Orden seguro (sin romper la app)

El truco es que **crear el rol no cambia nada** todavía: la app sigue con `postgres`
hasta que tú cambies `DATABASE_URL`. Así puedes probar antes de comprometerte.

### 1. Crear el rol
```bash
# Edita 01_create_app_role.sql: pon una contraseña real en <APP_DB_PASSWORD>
# y ajusta el nombre de la BD en el GRANT CONNECT si no es gestiqclouddb_dev.
psql "$DATABASE_URL" -f ops/security/01_create_app_role.sql
```
(La app sigue funcionando igual; aún usa `postgres`.)

### 2. Probar la conexión del rol nuevo SIN tocar producción
Arranca una instancia de prueba apuntando al rol nuevo:
```bash
# PowerShell
$env:DATABASE_URL = "postgresql://gestiq_app:<password>@localhost:5432/gestiqclouddb_dev"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8056
```
Comprueba que **lee y escribe** bien: entra a la app, lista productos, crea/edita
algo, abre algún módulo. Si algo da error tipo `permission denied for table X`,
significa que falta un GRANT (ver "Si falla").

### 3. Verificar que el aislamiento RLS ya funciona
Con el rol nuevo, esto debe mostrar que cada tenant ve solo lo suyo:
```bash
python -m pytest app/tests/security/test_session_isolation.py -k "isolat or superuser" --no-cov -q
# o el chequeo manual de aislamiento que se usó en la auditoría
```
El test `test_app_db_connection_is_not_superuser` debe **pasar** (ya no es superuser).

### 4. Hacerlo permanente
Cuando la prueba sea OK, cambia `DATABASE_URL` en la config real del **backend y de
los workers/celery** (mismo rol). Reinicia los servicios.

### 5. (Opcional) Hardening
```bash
psql "$DATABASE_URL" -f ops/security/02_force_rls_remaining.sql
```

## Si falla (permiso denegado)

No es grave y es reversible:
- **Volver atrás al instante:** cambia `DATABASE_URL` de nuevo a `postgres` y reinicia. La app vuelve a funcionar como antes.
- **Arreglar el permiso que falte** (como `postgres`):
  ```sql
  GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO gestiq_app;
  GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO gestiq_app;
  GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO gestiq_app;
  ```
- Repetir desde el paso 2.

## Notas

- Los jobs de sistema cross-tenant (`system_session`, `bot_session_scope`) **siguen funcionando** con el rol nuevo: setean `app.bypass_rls='true'` y la política `admin_bypass` lo permite. Esto es el bypass controlado e intencional (inventariado en `bypass-rls-register.md`).
- La contraseña del rol **no debe** subirse al repo; guárdala como secreto del entorno (VPS).
- Aplica el rol en **todos** los entornos (dev/staging/prod) para que el comportamiento sea consistente.
