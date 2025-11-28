# Runbooks

Guías rápidas para incidentes comunes. Ajusta comandos según host y credenciales.

## Migración fallida (SQL/Alembic)
1) Detener tráfico/escrituras si es necesario.
2) Revisar logs de la migración (Alembic o script SQL).
3) Validar estado de la DB (tablas a medio crear). Si es seguro, aplicar `down.sql` o `alembic downgrade -1`.
4) Restaurar backup (`pg_dump` previo) si quedó inconsistente:
   ```bash
   psql "$DATABASE_URL" < backup_YYYYMMDD.sql
   ```
5) Reaplicar migración tras corregir y correr smoke tests.

## Colas Celery/imports atascadas
1) Verificar `IMPORTS_ENABLED=1` y que el job runner esté activo (logs `app.startup`).
2) Revisar broker/Redis (si aplica):
   ```bash
   redis-cli -u $REDIS_URL ping
   redis-cli -u $REDIS_URL keys "imports:*"
   ```
3) Revisar estado en DB:
   ```bash
   psql "$DATABASE_URL" -c "select status, count(*) from import_batches group by 1";
   psql "$DATABASE_URL" -c "select status, count(*) from import_items group by 1";
   ```
4) Reintentar tarea o reencolar; revisar tablas de imports para bloqueos.
5) Reiniciar servicio si aplica: `systemctl restart gestiq-worker-imports` (según `ops/systemd/*`).

## Login 5xx o cookies
1) Revisar CORS y dominio de cookies (`COOKIE_DOMAIN`); en Cloudflare, validar reescritura en worker.
2) Confirmar certificados/HTTPS y SameSite adecuado.
3) Revisar rate limiting: logs de `RateLimitMiddleware` y env `RATE_LIMIT_ENABLED`.
4) Métricas: revisar 401/403 en dashboards; alertar si >5% en 5 min.

## Caché PWA / Service Worker (tenant)
1) Forzar recarga dura o borrar SW desde DevTools.
2) Confirmar versión build y assets nuevos desplegados.
3) Si se cambia `VITE_BASE_PATH`, regenerar build y limpiar caches.

## Pagos fallidos (Stripe/Payphone/Kushki)
1) Revisar logs `app.payments` y métricas de intentos/errores por proveedor.
2) Validar claves/entorno (sandbox/prod) y endpoints de callback.
3) Si hay webhooks: verificar firma/token y respuestas 2xx; revisar logs de callbacks.
4) Consultar intentos recientes en DB si existe tabla específica o en `pos_payments`.

## Facturación electrónica fallida
1) Revisar logs `app.einvoicing` y respuestas del proveedor.
2) Validar certificados/credenciales y entorno (sandbox/prod).
3) Consultar tabla `invoices`/`invoices_temp` por estado de error:
   ```bash
   psql "$DATABASE_URL" -c "select estado, count(*) from invoices group by 1";
   ```
4) Reintentar emisión si aplica, cuidando idempotencia.

## Recuperar acceso a DB
- Verificar conectividad: `psql "$DATABASE_URL" -c "select 1"`.
- Listar migraciones aplicadas (Alembic): `alembic history --verbose` o consulta a `alembic_version`.

## Observabilidad
- Logs: visor de Render/collector; filtrar por `request_id`.
- Métricas clave: auth 401/403, imports failed/pending, pagos intentos vs errores, e-invoicing fallos/latencia, health `/ready`.

## Cómo usar
- Ejecutar en orden, anotando cambios y timestamps.
- Documentar causa raíz y solución en el issue/ticket.

## Pendientes
- Añadir métricas/alertas esperadas para cada incidente.
- Añadir comandos específicos de storage/OCR si aplica.
