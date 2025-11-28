# Experiencia de desarrollo

## Prerrequisitos
- Python 3.11, Node 18+, PostgreSQL local (o Docker) y git.
- PowerShell (Windows) para el script `scripts/start_local.ps1`.
- Recomendado: `uv`/`pip` actualizado y npm >= 9.

## Setup local rápido
- Backend: `cd apps/backend && python -m venv .venv && .venv/Scripts/activate` (Windows) o `source .venv/bin/activate`; `pip install -r requirements.txt`; `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`.
- Frontends:
  - Admin: `cd apps/admin && npm install && npm run dev -- --host --port 8081`.
  - Tenant: `cd apps/tenant && npm install && npm run dev -- --host --port 8082`.
- Script unificado (Windows): `scripts/start_local.ps1` levanta backend + frontends con puertos 8000/8081/8082.

## Comandos rápidos
- Backend tests: `cd apps/backend && pytest -q app/tests`.
- Backend smoke endpoints: `python ops/scripts/check_endpoints.py` (desde raíz con env adecuado).
- Frontend typecheck/build:
  - Admin: `cd apps/admin && npm run typecheck && npm run build`.
  - Tenant: `cd apps/tenant && npm run typecheck && npm run build`.
- Migraciones Alembic: `cd apps/backend && alembic upgrade head`.
- Migraciones SQL idempotentes: `python ops/scripts/migrate_all_migrations_idempotent.py` (requiere `DATABASE_URL`).

## Convenciones
- `.env` en `apps/backend` con `ENV=development`. No commitear secretos.
- Branches: `main/master` protegidas (ver CI). Commits pequeños y claros.
- Estilo: mantener typing en Python y TypeScript; evitar `any`/`typing.Any` sin necesidad.

## Linters y tests
- Python: pytest (no hay linter configurado aquí; ejecutar formateo si se añade). CI crea `test.db` SQLite.
- Frontend: typecheck con `npm run typecheck` y build Vite. Añadir tests en Vitest donde aplique.

## Troubleshooting
- Puertos ocupados: `netstat -ano | findstr :8000` (Windows) y `taskkill /PID <PID> /F`.
- CORS/cookies: validar `COOKIE_DOMAIN` y orígenes en el worker (Cloudflare). En local, usar host-only.
- Cache PWA (tenant): forzar recarga dura o limpiar SW cuando no se reflejan cambios.
- Imports: si no arranca el runner, revisar `IMPORTS_ENABLED=1` y que existan tablas de imports.

## Pendientes
- Añadir scripts de make/just para automatizar comandos.
- Documentar setup con Docker/Compose si se agrega.
