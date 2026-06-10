# Despliegue (VPS + Render + Cloudflare)

> **Deploy real:** el backend productivo (API FastAPI, scripts SQL/migraciones, Redis, Celery, IA/OCR) corre en **VPS**. Render sirve únicamente los **frontends estáticos** (Admin y Tenant). Cloudflare Worker es el **edge gateway** (`/api/*`, CORS, cookies, request-id). `render.yaml` se mantiene como referencia de frontends e histórico/alternativo del backend, **no** como fuente del backend productivo.

| Componente | Dónde |
|---|---|
| Backend API FastAPI | VPS |
| Redis / Celery workers | VPS |
| Scripts SQL / migraciones | VPS |
| IA local / OCR | VPS |
| Admin / Tenant React (estáticos) | Render |
| Edge gateway (`/api/*`) | Cloudflare Worker |

## Backend (VPS)
1) Variables de entorno (en el VPS, no en Render): `DATABASE_URL` (o `DB_DSN`), `SECRET_KEY`, `JWT_SECRET_KEY`, `CORS_ORIGINS`, `COOKIE_DOMAIN`, `REDIS_URL`, `IMPORTS_ENABLED`, `CSRF_ENABLED`, claves de pagos/e-invoicing, `ENVIRONMENT=production`.
2) Proceso: `uvicorn app.main:app --host 0.0.0.0 --port <port>` (o gunicorn con uvicorn workers) gestionado por systemd/supervisor.
3) Redis + Celery workers/beat como servicios en el mismo VPS (broker Celery y tareas async: importador, OCR/IA, notificaciones, expiry).
4) Migraciones: ejecutar los scripts SQL manuales de `ops/migrations/` (up.sql/down.sql) en el VPS antes de arrancar la nueva versión cuando haya cambios de esquema. No usar Render para migraciones.
5) Healthchecks: `/health` y `/ready` según disponibilidad de Redis/DB.
6) Logs: runtime en el VPS; revisar `app.startup` y errores durante el deploy.

## Worker (Cloudflare)
1) Editar `workers/wrangler.toml` o usar `wrangler secret put` para: `TARGET`/`UPSTREAM_BASE`, `ALLOWED_ORIGINS`, `COOKIE_DOMAIN`, `HSTS_ENABLED`.
2) Publicar: `cd workers && wrangler publish`.
3) Rutas en Cloudflare: `admin.gestiqcloud.com/api/*` y `www.gestiqcloud.com/api/*` apuntando al worker.
4) Verificar CORS y cookies (SameSite/domain reescritos) con curl y navegador.

## DNS
- Registros en `ops/dns/*.txt`. Confirmar que los CNAME/A apuntan al servicio actual y SSL activo.

## Rollback
- Backend: en el VPS, volver a la versión anterior (checkout/imagen previa) y reiniciar el servicio. Si se aplicó migración destructiva, ejecutar el `down.sql` correspondiente de `ops/migrations/` o restaurar backup (`pg_dump`).
- Frontends: redeploy de la versión previa en Render.
- Worker: `wrangler publish` de la versión previa o revertir en el panel de Cloudflare.

## Checklist pre y post deploy
- Pre: migraciones listas y respaldos (`pg_dump`), variables de entorno completas, CORS/domains revisados, plan de rollback definido.
- Post: healthchecks OK, smoke tests (auth, imports, pagos/e-invoicing si aplica), logs sin errores, métricas/telemetría fluyen.

## Notas
- Mantener alineados los dominios de cookies entre backend y worker (`COOKIE_DOMAIN`).
- RLS ya activo; el backend setea el GUC `app.tenant_id` (no `app.current_tenant`) vía `app/config/database.py`. Ver `docs/seguridad.md`.
