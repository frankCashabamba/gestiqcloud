# ADR-0004: Estrategia de despliegue (Render + CF Worker + migraciones/RLS)

- Estado: Aceptado
- Fecha: 2025-xx-xx
- Autor: (tu nombre)

## Contexto
- Backend (FastAPI) se despliega en Render (`gestiqcloud-api`).
- Frontends (admin/tenant) en Render static (admin.gestiqcloud.com, www.gestiqcloud.com).
- Edge Gateway en Cloudflare Worker (ver ADR-0001) frente a admin/www/api.
- RLS habilitable en Postgres via flags y scripts; cron de migraciones en Render.

## Decisión
- Mantener Render como plataforma de API y frontends; CF Worker como gateway en prod.
- Orden de despliegue:
  1) Aplicar migraciones (Alembic o SQL); cron `gestiqcloud-migrate` puede ejecutarlas y aplicar RLS.
  2) Desplegar backend en Render (autodeploy filtrado por paths backend/ops/scripts).
  3) Actualizar Worker CF solo si cambia CORS/cookies/rutas.
  4) Desplegar frontends (admin/tenant) después de backend si hay cambios de contrato.
- RLS: flags `RUN_RLS_APPLY`, `RLS_SET_DEFAULT`, `RLS_SCHEMAS` en Render para aplicar políticas idempotentes; `ensure_rls` en app setea GUCs por request.

## Consecuencias
- Rollout controlado: migraciones antes de backend; Worker como capa independiente.
- Riesgo de mismatch si frontends consumen contratos cambiados: desplegar backend primero.
- Cron de migraciones y RLS aplica cambios idempotentes; monitorizar.

## Referencias
- `render.yaml` (servicios web/worker/beat/cron, flags RLS, OTEL).
- ADR-0001 (Worker), ADR-0003 (RLS), ADR-0002 (SQLite en CI).
