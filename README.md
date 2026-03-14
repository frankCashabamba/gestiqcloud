# GestiQCloud

ERP/CRM multi-tenant para España y Ecuador. Backend en FastAPI, frontends React (Admin + Tenant PWA), edge gateway en Cloudflare Workers, desplegado en Render.

## Arquitectura

```
gestiqcloud/
├── apps/
│   ├── backend/        FastAPI + SQLAlchemy + Pydantic v2
│   ├── admin/          React + Vite (panel administrador)
│   ├── tenant/         React + Vite (app tenant, PWA)
│   └── packages/       Librerías TS compartidas
│       ├── api-types/      Tipos de API
│       ├── auth-core/      Helpers de auth/sesión
│       ├── http-core/      Cliente HTTP
│       ├── endpoints/      Definiciones de endpoints
│       ├── ui/             Componentes React + Tailwind preset
│       ├── pwa/            Plugin PWA/SW
│       ├── telemetry/      OpenTelemetry helpers
│       ├── utils/          Utilidades comunes
│       └── zod/            Schemas de validación
├── ops/
│   ├── migrations/     Migraciones SQL (fuente de verdad)
│   ├── scripts/        Scripts de orquestación y CI
│   ├── dns/            Registros DNS
│   ├── systemd/        Servicios systemd
│   ├── ci/             Helpers de CI
│   └── k6/             Tests de carga
├── workers/            Cloudflare Worker (CORS, cookies, request IDs)
├── scripts/            Scripts de utilidad y desarrollo local
├── e2e/                Tests end-to-end (Playwright)
├── docs/               Documentación técnica
└── data/               Datos de feedback
```

## Stack

| Componente | Tecnología |
|---|---|
| Backend API | Python 3.13, FastAPI, SQLAlchemy 2, Pydantic v2 |
| Base de datos | PostgreSQL (SQLite en CI) |
| Frontends | React 18, Vite, TypeScript, Tailwind CSS |
| Workers | Celery (colas SRI/SII + importaciones) |
| Edge | Cloudflare Workers |
| Observabilidad | OpenTelemetry, Sentry |
| OCR/AI | EasyOCR, Tesseract, Ollama/OpenAI |
| Deploy | Render (API + static sites + workers + cron) |

## Módulos de negocio

Productos · Ventas · POS · Compras · Gastos · Inventario · Producción (costeo/recetas) · Contabilidad · Facturación · Facturación electrónica (SRI/SII) · Clientes/CRM · Proveedores · RRHH · Pagos (Stripe/Payphone/Kushki) · Importador de documentos · Copilot AI · Reportes · Webhooks · Notificaciones

## Arranque local

### Requisitos

- Python 3.11+ con venv
- Node 18+
- PostgreSQL (o SQLite para dev rápido)

### Setup

```powershell
# 1. Variables de entorno
cp .env.example .env
# Editar .env con tus valores

# 2. Backend
cd apps/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 3. Admin
cd apps/admin
npm install
npm run dev -- --host --port 8081

# 4. Tenant
cd apps/tenant
npm install
npm run dev -- --host --port 8082
```

O con el script unificado (Windows):

```powershell
scripts\start_local.ps1
```

### Puertos

| Servicio | URL |
|---|---|
| Backend API | http://localhost:8000 |
| Admin | http://localhost:8081 |
| Tenant | http://localhost:8082 |
| Swagger | http://localhost:8000/docs |

## Migraciones

La fuente de verdad son los archivos SQL en `ops/migrations/`. Ejecutar:

```bash
python ops/scripts/migrate_all_migrations_idempotent.py
```

Requiere `DATABASE_URL` en el entorno. La tabla `_migrations` trackea qué se ha aplicado.

En producción, el cron job `gestiqcloud-migrate` en Render aplica migraciones automáticamente (configurable en `render.yaml`).

## Tests

```bash
# Backend (pytest, usa SQLite)
cd apps/backend
pytest -q app/tests

# Frontend typecheck
cd apps/admin && npm run typecheck
cd apps/tenant && npm run typecheck

# E2E (Playwright)
npx playwright test
```

## CI/CD

GitHub Actions (`.github/workflows/`):

| Workflow | Función |
|---|---|
| `ci.yml` | Tests backend + typecheck frontends |
| `backend.yml` | Build y validación backend |
| `webapps.yml` | Build admin + tenant |
| `worker.yml` | Validación Cloudflare Worker |
| `db-pipeline.yml` | Pipeline de migraciones |
| `migrate-on-migrations.yml` | Auto-migración en push a `ops/migrations/` |

Deploy automático en Render al pushear a `main` (filtrado por paths en `render.yaml`).

## Deploy (Producción)

| Componente | Dónde | Motivo |
|---|---|---|
| **Backend API** (FastAPI) | VPS | AI/OCR, Redis, Celery requieren recursos locales |
| **Redis** | VPS | Broker para Celery y caché |
| **Celery workers** (SRI/SII, imports) | VPS | Procesan colas con acceso a Redis y AI |
| **Celery beat** | VPS | Scheduler de tareas periódicas |
| **Tenant** (React SPA) | Render static | `gestiqcloud-tenant` |
| **Admin** (React SPA) | Render static | `gestiqcloud-admin` |
| **Edge gateway** | Cloudflare Workers | CORS, cookies, request IDs |

Configuración de referencia para Render en `render.yaml` (frontends). Edge gateway en `workers/edge-gateway.js`.

## Documentación

Índice completo en [`docs/README.md`](docs/README.md). Highlights:

- [Arquitectura](docs/arquitectura.md)
- [Backend (referencia)](docs/backend.md)
- [Contratos de API](docs/api-contracts.md)
- [Deploy](docs/deploy.md)
- [Seguridad](docs/seguridad.md)
- [Pagos y facturación electrónica](docs/payments-einvoicing.md)
- [ADRs](docs/adr/)
- [Runbooks](docs/runbooks/)
