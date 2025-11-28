# Despliegue (Render + Cloudflare)

## Backend (Render)
1) Variables de entorno: `DATABASE_URL`, `SECRET_KEY`, `JWT_SECRET_KEY`, `CORS_ORIGINS`, `COOKIE_DOMAIN`, `IMPORTS_ENABLED`, claves de pagos/e-invoicing, `ENV=production`.
2) Build/run command: usar `uvicorn app.main:app --host 0.0.0.0 --port $PORT` (o gunicorn con uvicorn workers si se habilita).
3) Migraciones: aplicar antes del despliegue si son manuales (`ops/scripts/migrate_all_migrations_idempotent.py` o SQL). Alembic puede correr en release step.
4) Healthchecks: apuntar a `/health` y `/ready` según disponibilidad de Redis/DB.
5) Logs: revisar startup (`app.startup`) y errores durante el deploy.

## Worker (Cloudflare)
1) Editar `workers/wrangler.toml` o usar `wrangler secret put` para: `TARGET`/`UPSTREAM_BASE`, `ALLOWED_ORIGINS`, `COOKIE_DOMAIN`, `HSTS_ENABLED`.
2) Publicar: `cd workers && wrangler publish`.
3) Rutas en Cloudflare: `admin.gestiqcloud.com/api/*` y `www.gestiqcloud.com/api/*` apuntando al worker.
4) Verificar CORS y cookies (SameSite/domain reescritos) con curl y navegador.

## DNS
- Registros en `ops/dns/*.txt`. Confirmar que los CNAME/A apuntan al servicio actual y SSL activo.

## Rollback
- Backend: revertir deploy a la versión anterior en Render. Si se aplicó migración destructiva, restaurar backup (`pg_dump`) y redeploy.
- Worker: `wrangler publish` de la versión previa o revertir en el panel de Cloudflare.

## Checklist pre y post deploy
- Pre: migraciones listas y respaldos (`pg_dump`), variables de entorno completas, CORS/domains revisados, plan de rollback definido.
- Post: healthchecks OK, smoke tests (auth, imports, pagos/e-invoicing si aplica), logs sin errores, métricas/telemetría fluyen.

## Notas
- Mantener alineados los dominios de cookies entre backend y worker (`COOKIE_DOMAIN`).
- Si se activa RLS, desplegar primero cambios de app que setean `app.current_tenant`, luego políticas en DB.
