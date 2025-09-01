# AGENTS.md

Guía práctica para colaborar (humanos y agentes) en este monorepo con FastAPI (backend), React+Vite (frontends), Postgres y Docker/Compose.

## Propósito
- Alinear cómo arrancar, desarrollar, probar y depurar servicios.
- Documentar variables de entorno y scripts típicos por servicio.
- Establecer un flujo de trabajo seguro para agentes (cambios mínimos, pruebas, formato).

## Arquitectura (resumen)
- Backend: FastAPI + Uvicorn. Migraciones con Alembic. Cliente DB vía SQLAlchemy/psycopg.
- Frontend(s): React + Vite. Comunicación con el backend vía REST/JSON.
- Base de datos: Postgres (desarrollo y producción).
- Orquestación: Docker Compose para entorno local coherente.

## Estructura del monorepo
Los nombres pueden variar; detecta rutas reales listando carpetas en la raíz.
Suelen existir directorios como:
- `backend/`: código FastAPI, `app/`, `alembic/`, `pyproject.toml` o `requirements.txt`.
- `frontend-*/` o `apps/*`: apps React+Vite con `package.json` y `vite.config.*`.
- `infra/` o raíz: `docker-compose.yml` (o `compose.yaml`) y archivos `.env*`.

Para confirmar rutas, busca marcadores:
- Backend: `rg -n "FastAPI\(|uvicorn|alembic"` y `rg --files backend`.
- Frontends: `rg -n "vite"` o `rg --files | rg "vite.config|package.json"`.

## Requisitos locales
- Docker Desktop 4.x+ (Compose v2: `docker compose …`).
- Alternativa sin Docker: Python 3.11+, Node.js 18+ (o 20+), pnpm/npm.

## Variables de entorno
Define valores en `.env` (raíz) y/o específicos por servicio:
- Backend (`backend/.env`):
  - `DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/app`
  - `UVICORN_HOST=0.0.0.0`, `UVICORN_PORT=8000`, `DEBUG=true`
  - `CORS_ORIGINS=http://localhost:5173,http://localhost:5174`
- Frontend (`<frontend>/.env`):
  - `VITE_API_URL=http://localhost:8000`
- DB (Compose o `.env` raíz):
  - `POSTGRES_DB=app`, `POSTGRES_USER=postgres`, `POSTGRES_PASSWORD=postgres`
  - `POSTGRES_HOST=db`, `POSTGRES_PORT=5432`

Ajusta orígenes CORS a los puertos reales de cada frontend.

## Arranque con Docker Compose
En la raíz del repo:
- Construir y levantar: `docker compose up -d --build`
- Ver logs por servicio: `docker compose logs -f backend` (o `frontend-web`, `db`)
- Reconstruir solo backend: `docker compose build backend && docker compose up -d backend`
- Apagar: `docker compose down` (añade `-v` para borrar volúmenes locales)

Convenciones de servicios (pueden variar):
- Backend en `http://localhost:8000` → docs: `/docs` y `/redoc`.
- Frontend(s) Vite en `http://localhost:5173`, `5174`, …
- Postgres expuesto en `localhost:5432` (solo dev).

## Desarrollo sin Docker
Backend (desde `backend/`):
- Crear entorno: `python -m venv .venv && source .venv/bin/activate` (Win: `\.venv\Scripts\activate`)
- Instalar deps: `pip install -r requirements.txt` o `poetry install`
- Migraciones: `alembic upgrade head`
- Ejecutar: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

Frontend (desde cada `<frontend>/`):
- Instalar deps: `pnpm i` (o `npm i`/`yarn`)
- Ejecutar: `pnpm dev` (o `npm run dev`)

Conexión a DB local: exporta `DATABASE_URL` apuntando a tu Postgres (Docker o local).

## Migraciones (Alembic)
- Crear revisión: `alembic revision --autogenerate -m "<mensaje>"`
- Aplicar: `alembic upgrade head`
- Revertir: `alembic downgrade -1`
Asegúrate de que los modelos reflejen el estado deseado antes de autogenerar.

## Scripts comunes
Backend:
- Formato/lint (si configurado): `ruff check .`, `black .`, `isort .`
- Test: `pytest -q`
- Tipado (opcional): `mypy .`

Frontends:
- Dev: `pnpm dev`
- Build: `pnpm build`
- Preview: `pnpm preview`
- Test: `pnpm test` (vitest) y lint: `pnpm lint`, formato: `pnpm format`

## Pruebas y calidad
- Prioriza pruebas unitarias en backend con `pytest` y en frontend con `vitest`.
- Ejecuta linters/formatters antes de abrir PRs o terminar cambios.
- No cambies dependencias o configuraciones globales sin necesidad.

## Documentación de API
- Swagger UI: `http://localhost:<puerto-backend>/docs`
- Redoc: `http://localhost:<puerto-backend>/redoc`
- Healthcheck típico: `GET /health` o `GET /` (verifica en rutas reales).

### Seguridad (CSRF y cookies)
- Verificación CSRF: se realiza exclusivamente vía el middleware `RequireCSRFMiddleware`.
  - Métodos seguros (`GET/HEAD/OPTIONS`): exentos.
  - Exenciones por sufijo: `/auth/login`, `/auth/refresh`, `/auth/logout` (aplican en admin y tenant).
  - Encabezados aceptados: `X-CSRF-Token` o `X-CSRF` (double-submit cookie `csrf_token`).
  - Emisión: los endpoints de login establecen cookie `csrf_token` legible por JS.
- Cookies de refresh:
  - Admin: path `'/api/v1/admin/auth'`.
  - Tenant: path `'/api/v1/tenant/auth'`.
  - Atributos: `HttpOnly`, `SameSite` (`lax` en dev, `strict` en prod), `Secure` en producción.

## Datos de ejemplo
- Si existe `backend/scripts/seed.py`: `python backend/scripts/seed.py` (o vía Compose `docker compose exec backend python scripts/seed.py`).
- Alternativa: archivos SQL en `infra/sql/` aplicados al iniciar DB.

## Flujo de trabajo para agentes
- Descubrimiento: lista archivos y busca marcadores (FastAPI, Vite, Alembic).
- Cambios mínimos: modifica solo lo necesario; respeta estilos existentes.
- Pruebas primero: añade o ajusta tests cerca del código tocado cuando existan patrones.
- Formato: ejecuta formatters/lints configurados; no introduzcas nuevas herramientas.
- Validación: levanta servicios con Compose o ejecuta targets de test/build.
- Evita cambios colaterales: no renombres rutas/vars a menos que sea requerido.

## Solución de problemas
- Puertos ocupados: cambia `UVICORN_PORT`/puertos Vite o detén procesos en conflicto.
- CORS: actualiza `CORS_ORIGINS` en backend y `VITE_API_URL` en frontends.
- Migraciones fallan: revisa `alembic.ini`, `env.py` y `target_metadata`; elimina/recrea solo en dev si es seguro.
- Conexión DB: confirma `POSTGRES_*` y accesibilidad `db:5432` (en Compose) o `localhost:5432`.
- 404 desde frontend: valida rutas base y proxies en `vite.config.*`.
- Redis (sesiones): si `REDIS_URL` está definido, las sesiones se guardan en Redis.
  - Healthcheck: `GET /health/redis` → `{ enabled, ok }` (503 si falla el ping).
  - En local, puedes arrancar Redis con `docker run -p 6379:6379 -d redis:7`.

## Producción (pistas)
- Variables separadas: `.env.production` y secretos fuera del repo.
- Builds reproducibles: `docker compose -f compose.yml -f compose.prod.yml up -d --build` (si existe override).
- Migraciones en deploy: ejecutar `alembic upgrade head` como parte del entrypoint.

## Convenciones sugeridas
- Backend en `:8000`, frontends desde `:5173+N`.
- Directorios consistentes: `backend/`, `apps/<nombre-frontend>/`.
- Nombres de servicios Compose: `backend`, `db`, `frontend-<nombre>`.

---
Si alguna ruta, puerto o script difiere en este repo, actualiza este archivo reflejando los nombres reales tras inspeccionarlos con `rg`/`ls`.
