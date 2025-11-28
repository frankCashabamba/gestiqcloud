# Entornos y estado

## Producción
- API: Render `gestiqcloud-api` → https://api.gestiqcloud.com (proxy vía Worker CF en dominios admin/www).
- Frontends: `gestiqcloud-tenant` en https://www.gestiqcloud.com, `gestiqcloud-admin` en https://admin.gestiqcloud.com.
- Worker CF: rutas `admin.gestiqcloud.com/api/*` y `www.gestiqcloud.com/api/*` hacia Render (ver ADR-0001).
- RLS: flags en `render.yaml` `RUN_RLS_APPLY=1`, `RLS_SET_DEFAULT=1` (confirmar estado aplicado en DB).
- Pagos: Stripe/Payphone/Kushki (claves como secretos en Render; sandbox/prod según configuración actual).
- E-invoicing: gestiona SRI/Facturae (credenciales como secretos; confirmar modo sandbox/prod en env).
- Imports: `IMPORTS_ENABLED=0` en Render por defecto (activar según necesidad).
- Observabilidad: OTEL_ENABLED=1 (backend/worker/beat) con endpoint OTLP configurado como secreto.
- Secretos: DATABASE_URL, JWT_SECRET_KEY, SECRET_KEY, correo, pagos, OTEL endpoint. Responsable: completar.

## Staging/QA
- No existe entorno separado actualmente (se usa dev local y prod).
- API/Front/Worker: N/A (pendiente si se crea).
- RLS: N/A.
- Pagos/e-invoicing: N/A (usar sandbox en entornos no prod si se habilita).
- Observabilidad: N/A.
- Secretos: N/A.

## Dev/local
- Script `scripts/start_local.ps1`; puertos 8000 (backend), 8081 (admin), 8082 (tenant).
- DB: SQLite (`test.db`) o Postgres local; `IMPORTS_ENABLED` opcional.
- OTEL/redis desactivados por defecto.

## Checklist a mantener
- URLs por entorno y rutas CF activas.
- Estado de RLS aplicado en DB.
- Proveedores de pago/e-invoicing y modo (sandbox/prod).
- OTEL exporter y panel de monitoreo usado.
- Responsables de secretos por entorno.

## Procedimientos mínimos
- Smoke test post-deploy: login admin/tenant, endpoint de salud, acción crítica por dominio (ventas/pagos/e-invoicing/imports si habilitado).
- Revisión de variables secretas antes de desplegar (Render/Cloudflare): claves JWT/SECRET_KEY, pagos, e-invoicing, OTEL, correo.
- Confirmar modo sandbox/prod en pagos/e-invoicing según entorno; revisar callbacks/domino asociado.
- Para cambios de RLS o migraciones sensibles: aplicar en ventana controlada y validar con consulta de verificación (leer conteos por tenant).
- `alembic_version` se usa solo como marcador de migración aplicada; no se consulta en app. Verificar migraciones con el script `python ops/scripts/migrate_all_migrations_idempotent.py` y, si se necesita, con `alembic current`.

## Pendientes
- Definir responsable y checklist por entorno (quién aprueba despliegue, contacto on-call).
- Documentar comandos exactos de verificación de RLS y migraciones (SQL o scripts).
- Añadir matriz de features/flags activos por entorno (IMPORTS_ENABLED, OTEL, etc.).

## Comandos útiles (RLS/GUC)
- Ver GUCs seteadas (Postgres): `SELECT current_setting('app.tenant_id', true), current_setting('app.user_id', true);`
- Validar que las políticas existen: `SELECT * FROM pg_policies WHERE schemaname = 'public' AND tablename IN ('pos_receipts','facturas','payments');`
- Probar aislamiento (ejemplo): `SET LOCAL app.tenant_id = '<uuid>' ; SELECT count(*) FROM pos_receipts;` (debe devolver solo registros del tenant).
