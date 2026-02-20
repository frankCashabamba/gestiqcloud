# Backend (referencia completa)

Backend API multi-tenant construido con FastAPI + SQLAlchemy, orientado a ERP/CRM con flujos de importación masiva, facturación y módulos de negocio.

## Stack y entrypoints
- Framework: FastAPI, Pydantic v2, SQLAlchemy (sync/async ready), Alembic para migraciones.
- Punto de entrada: `app/main.py` (CORS, middlewares, router, docs y healthchecks).
- Router dinámico: `app/platform/http/router.py` monta los módulos modernos (`app/modules/*/interface/http`). Legacy routers se mantienen como respaldo en `app/routers/*`.
- Telemetría: `app/telemetry/otel.py` inicializa OpenTelemetry para FastAPI.

## Configuración y entorno
- Config central: `app/config/settings.py` (carga `.env`/`.env.production` o `ENV_FILE`). Variables clave: `DATABASE_URL`, `SECRET_KEY`, `JWT_SECRET_KEY`, `ENV`, `CORS_ORIGINS`, `COOKIE_DOMAIN`, `IMPORTS_ENABLED`, `RATE_LIMIT_ENABLED`, `ENDPOINT_RATE_LIMIT_ENABLED`, `REDIS_URL`.
- Database: `app/config/database.py` define el engine y `Base`. `app/db/session.py` para sesiones.
- Logging: `app/core/logging.py`, niveles por `LOG_LEVEL`.

## Arranque y middlewares (app/main.py)
- Descarga assets de Swagger/ReDoc en `app/static/docs` si faltan.
- Middlewares: reescritura de `/v1`→`/api/v1`, UTF-8, `CORSMiddleware`, sesiones server-side (`SessionMiddlewareServerSide`), `RequestLogMiddleware`, rate limiting global (`RateLimitMiddleware`) y por endpoint (`EndpointRateLimiter`), cabeceras de seguridad (`security_headers_middleware`).
- Health: `/health` (básico), `/ready` (DB/Redis), `/healthz` (HEAD/GET) y raíz `/`.
- Static: monta `/uploads` si existe `UPLOADS_DIR` y está habilitado.

## Seguridad y auth
- Autenticación por cookies HttpOnly (`access_token` SameSite=Lax, `refresh_token` SameSite=None; Secure). Dominio configurable (`COOKIE_DOMAIN`), alineado con el worker de Cloudflare.
- JWT configurable (`JWT_*`); claves secretas nunca se commitean.
- Permisos y guardas: `app/core/permissions.py`, `app/core/access_guard.py`, `app/platform/http/security/*` para guards/csrf/authz.
- Rate limiting crítico en login/reset password (configurable por env).
- Sesiones server-side opcionales (Redis soportado si se configura en settings).

## Base de datos y migraciones
- Modelos: `app/db/models.py` y modelos por dominio en `app/models/*` (ventas, compras, contabilidad, etc.).
- Migraciones: Alembic en `apps/backend/alembic/` (ver `apps/backend/alembic/README.md`). Migraciones SQL manuales en `ops/migrations/` (ver `docs/datos-migraciones.md`).
- Multi-tenant: `tenant_id` presente en tablas de negocio; preparado para RLS (ver `docs/seguridad.md`).

## Multitenancy
- Contexto de empresa/tenant gestionado en `app/core/tenancy.py` y `app/core/sessions.py`.
- Configuración dinámica de campos por módulo: `app/services/field_config.py` y endpoints en `app/modules/settings/interface/http/tenant.py`.
- Cookies con dominio `.gestiqcloud.com` y CORS estrictos (combinado con el worker de Cloudflare).

## Observabilidad y métricas
- OpenTelemetry (`app/telemetry/otel.py`) y métricas en `app/metrics/`. Configurar exporters (OTLP/HTTP) vía env si se habilita.
- Logging estructurado de requests (`RequestLogMiddleware`) y propagación de request IDs (alineado con worker).
- Logs clave: `app.startup`, `app.router`, `app.health`, `app.cors`; habilitar nivel DEBUG solo en entornos de desarrollo.

## Background/Workers
- Imports job runner: se inicializa tras el bind si `IMPORTS_ENABLED=1` y existen tablas de imports (ver `app/main.py`).
- Celery (para imports/otros): config en `app/config/celery_config.py`; tareas en `app/workers/*` y `app/modules/imports/application/tasks/*`.

## Estructura por carpetas (resumen)
- `admin/`: APIs/servicios específicos para vistas administrativas.
- `api/`: endpoints públicos genéricos (`api/v1` base).
- `config/`: settings, DB, Celery.
- `core/`: auth, permisos, sesiones, cookies, logging, rate limiting, utils base.
- `db/`: base SQLAlchemy y sesiones.
- `middleware/`: middlewares custom (logging, rate limit, seguridad).
- `models/`: modelos compartidos y por dominio.
- `modules/`: dominios de negocio (ver abajo).
- `platform/http/`: router dinámico y seguridad HTTP.
- `routers/`: routers legacy mantenidos por compatibilidad.
- `schemas/`: Pydantic schemas (auth, ventas, contabilidad, etc.).
- `services/`: servicios transversales (payments, onboarding, defaults, etc.).
- `settings/`: configuraciones de módulos (roles, inventario, etc.).
- `shared/`: DTOs/utilidades compartidas.
- `templates/`: HTML/PDF para facturación/POS y landing.
- `tests/`: suite de pytest (smoke, módulos clave, auth, imports, etc.).
- `workers/`: tareas Celery/async.

## Módulos principales (`app/modules`)
- `identity`: login, sesiones, refresh, perfiles, JWT/refresh tokens.
- `settings`: configuración de campos y módulos, modos por tenant/sector, endpoints admin/tenant.
- `modulos`: catálogo y asignación de módulos por empresa/tenant.
- `admin_config`: catálogos globales (sectores, tipos de negocio/empresa, países, monedas, timezones, idiomas, plantillas de UI, horarios).
- `products`: catálogo de productos, categorías, precios, repositorios.
- `sales` / `pos`: ventas/POS, recibos, líneas, pagos asociados.
- `purchases`: compras y líneas de compra.
- `expenses`: gastos.
- `finanzas`: caja/bancos, conciliaciones básicas.
- `accounting` / `contabilidad`: plan de cuentas, asientos, reportes contables.
- `invoicing` / `einvoicing`: facturación y facturación electrónica; plantillas PDF/HTML.
- `inventory`: inventario, movimientos, alertas.
- `production`: órdenes de producción, recetas, ingredientes.
- `suppliers`: proveedores y contactos.
- `clients` / `crm`: clientes/CRM y oportunidades.
- `hr`: nómina/empleados.
- `imports`: pipeline de importación (OCR, clasificación, preview, publish), APIs (`interface/http`), tareas (`application/tasks`), configuración de alias/DSL, AI (`imports/ai/*`).
- `templates`: gestión de plantillas (email/UI/pdf) por tenant/sector.
- `registry`: registro de empresas/tenants y asignación de módulos.
- `export`: endpoints de exportación.
- `reconciliation`/`payments`: integraciones de pago (Stripe, Payphone, Kushki) en `app/services/payments/*`.
- `copilot` / `ai_agent`: endpoints/servicios de asistencia AI (si se despliega).
- `webhooks`: recepción/eventos externos.
- `shared`: servicios base y repositorios reutilizables.

## Servicios transversales
- Pagos: `app/services/payments/{stripe,payphone,kushki}_provider.py`.
- Notificaciones: `app/workers/notifications.py` y `app/services/notifications.py`.
- Onboarding/sector: `app/services/tenant_onboarding.py`, `app/services/sector_templates.py`, `app/services/sector_defaults.py`.
- Número/series: `app/services/numbering.py` y `app/modules/shared/services/numbering.py`.
- Imports: `app/modules/imports/application/job_runner.py`, `.../tasks/*`, `.../interface/http/*`.

## Módulos (índice)
- Ver `docs/modules-index.md` para referencias rápidas por dominio y enlaces a README de módulo.
- Módulos con README existente: `app/modules/settings/README.md`, `app/modules/shared/README.md`, varios documentos en `app/modules/imports/*.md`.

## Imports (guía rápida)
- Router: `/api/v1/imports/*` se monta si `IMPORTS_ENABLED=1` y tablas de imports existen.
- Documentación detallada en `app/modules/imports/README.md` y `app/modules/imports/README_MODULE.md` (histórico en `_legacy_docs/`).
- Flujo: `batches` → `ingest` → `validate` → `promote` (+ fotos/OCR opcional).
- Env relevantes: `IMPORTS_ENABLED`, credenciales de storage/OCR/AI si aplica.
- Ejemplos curl:
  ```bash
  # Crear batch
  curl -s -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d '{"source_type":"receipts","origin":"ocr"}' \
    http://localhost:8000/api/v1/imports/batches

  # Ingestar filas
  curl -s -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d '{"rows":[{"sku":"123","name":"Prod"}],"defaults":{"tenant_id":"..."}}' \
    http://localhost:8000/api/v1/imports/batches/$BATCH/ingest

  # Validar y promover
  curl -s -X POST -H "Authorization: Bearer $TOKEN" \
    http://localhost:8000/api/v1/imports/batches/$BATCH/validate
  curl -s -X POST -H "Authorization: Bearer $TOKEN" \
    http://localhost:8000/api/v1/imports/batches/$BATCH/promote
  ```

## Pagos y e-invoicing
- Proveedores de pago: Stripe, Payphone, Kushki (`app/services/payments/*`). Configurar API keys vía env.
- Facturación electrónica: módulo `einvoicing` (Ecuador/ES) y plantillas en `templates/pdf`.
- Endpoints clave: `/api/v1/einvoicing/*`, `/api/v1/payments/*` (según módulo).
- Recomendado: entorno sandbox de cada proveedor antes de producción; validar webhooks si aplica.
- Detalle ampliado: ver `docs/payments-einvoicing.md`.

## Tests y calidad
- Suite: `app/tests/` (smoke, auth, rate limit, imports, POS/ventas, contabilidad, e-invoicing, pagos básicos).
- Gaps sugeridos: pruebas de RLS (cuando se active), flujos completos de payments/e-invoicing y pipelines de imports con fotos/OCR.
- CI: `Base.metadata.create_all` sobre SQLite, `pytest -q app/tests`, smoke de endpoints con `ops/scripts/check_endpoints.py`.

## Rutas/Health/DOCS
- Health: `/health`, `/ready`, `/healthz`.
- Docs: `/docs` (Swagger UI) y `/redoc` (assets locales en `static/docs`).
- API base: `/api/v1` (routers modernos); rutas legacy reescritas desde `/v1/*`.

## Operación
- Variables sensibles via `.env` (no commitear). Para producción usar secretos gestionados.
- Migraciones: preferir Alembic; para snapshots completos ver `ops/migrations`. Seguir guías de `docs/datos-migraciones.md`.
- CORS/cookies: trabajar en conjunto con el Cloudflare Worker (`workers/edge-gateway.js`), que reescribe `Set-Cookie` y limita orígenes.
- Activación opcional de RLS: ver `docs/seguridad.md` para políticas por `tenant_id`.

## Enlaces útiles
- README operativo: `apps/backend/README.md` (comandos y curl).
- Docs generales: `docs/arquitectura.md`, `docs/seguridad.md`, `docs/datos-migraciones.md`.
- Ejemplos HTTP: `docs/examples-curl.md`.
- Pagos/e-invoicing: `docs/payments-einvoicing.md`.
- Observabilidad/alertas: `docs/observabilidad.md`.
