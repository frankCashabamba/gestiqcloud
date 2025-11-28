# Backend FastAPI

Backend API multi-tenant (FastAPI + SQLAlchemy) con sesiones por cookie y soporte de importaciones masivas.

## Stack y estructura
- FastAPI, SQLAlchemy, Pydantic v2, Alembic.
- `app/main.py`: arranque, CORS, rate limiting, mounting de routers y docs.
- `app/config/`: settings (.env), DB engine, Celery config.
- `app/core/`: auth (JWT/cookies), permisos, sesiones server-side, logging, rate limits.
- `app/modules/`: dominios (ventas, compras, facturación, imports, settings, etc.) con `application/infrastructure/interface`.
- `app/platform/http/router.py`: montaje automático de routers de módulos.
- `app/templates/`: HTML/PDF para facturación y POS.

## Configuración/env vars (principales)
- `DATABASE_URL` (Postgres o SQLite), `ENV` (`development`/`production`), `SECRET_KEY`, `JWT_SECRET_KEY`.
- CORS/cookies: `CORS_ORIGINS`, `COOKIE_DOMAIN`, `SESSION_COOKIE_NAME`, `CORS_ALLOW_METHODS`.
- Importaciones: `IMPORTS_ENABLED` (1/0) y tablas creadas.
- Redis opcional: `REDIS_URL` (para ready check y caché de sesiones si se configura).

## Cómo correr (dev)
```bash
cd apps/backend
python -m venv .venv && source .venv/bin/activate  # en Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Docs: http://localhost:8000/docs y /redoc. Health: `/health`, `/ready`.

## Tests
```bash
cd apps/backend
pytest -q app/tests
python ../..//ops/scripts/check_endpoints.py  # smoke de endpoints FE/BE
```

## Migraciones
- Alembic en `apps/backend/alembic/`. Config en `alembic.ini`.
- Comandos típicos: `alembic revision --autogenerate -m "msg"`, `alembic upgrade head`.
- Migraciones SQL manuales viven en `ops/migrations/` (ver `docs/datos-migraciones.md`).

## Endpoints clave
- Auth: `/api/v1/tenant/auth/login`, `/api/v1/admin/auth/login`.
- Settings y campos dinámicos: `/api/v1/tenant/settings/fields`, `/api/v1/admin/field-config/*`.
- Imports: `/api/v1/imports/*` (preview, upload, publish, ai).
- Salud: `/health`, `/ready`.

### Ejemplos rápidos (curl)
```bash
# Health
curl -s http://localhost:8000/health

# Login tenant (ajusta credenciales)
curl -i -X POST http://localhost:8000/api/v1/tenant/auth/login \
  -H "Content-Type: application/json" \
  --data '{"identificador":"USER","password":"secret"}' -c cookies.txt

# Campos configurables (clientes) para un tenant
curl -s "http://localhost:8000/api/v1/tenant/settings/fields?module=clientes&empresa=kusi-panaderia" \
  -b cookies.txt

# Login admin y lectura de empresas
curl -i -X POST http://localhost:8000/api/v1/admin/auth/login \
  -H "Content-Type: application/json" \
  --data '{"identificador":"ADMIN","password":"secret"}' -c admin.cookies.txt
curl -s http://localhost:8000/api/v1/admin/empresas -b admin.cookies.txt

# Refresh token tenant (usa cookies previas)
curl -i -X POST http://localhost:8000/api/v1/tenant/auth/refresh -b cookies.txt -c cookies.txt
```

## Troubleshooting
- Si `/docs` falla: revisa que se hayan descargado assets (startup los baja a `app/static/docs`).
- Si imports no arrancan: confirma `IMPORTS_ENABLED=1` y tablas de imports creadas (ver `app/main.py`).
- Problemas CORS/cookies: validar dominios en env y configuración del worker (Cloudflare) para reescribir cookies.

## Pendientes
- Documentar módulos por dominio y flujos de negocio.
- Añadir ejemplos de curl/httpie por endpoint crítico.
