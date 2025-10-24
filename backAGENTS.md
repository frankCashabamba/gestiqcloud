# Repository Guidelines

## Project Structure & Module Organization
- Backend: `apps/backend` (FastAPI). DB via Postgres.
- Frontends: `apps/admin` (panel admin) y `apps/tenant` (app tenant), Vite + TS.
- Shared packages: `apps/packages/*` (`ui`, `http-core`, `endpoints`, `domain`, `utils`, etc.).
- Infra: `docker-compose.yml` en la raíz; scripts en `scripts/` (`init.ps1` y `init.sh`).

## Build, Test, and Development Commands
- Compose: `docker compose up -d --build` (admin: :8081, tenant: :8082, backend: :8000).
- Logs: `docker compose logs -f backend|admin|tenant`.
- Scripts rápidos: `powershell -File scripts/init.ps1 up|down|rebuild|typecheck|logs backend` (o `bash scripts/init.sh ...`).
- Frontend local: `cd apps/admin && npm run dev` (igual para `apps/tenant`).

## Coding Style & Naming Conventions
- Python: Black/Isort/Ruff si están configurados. 4 espacios; snake_case; clases en PascalCase.
- TypeScript/React: ESLint/Prettier si existen. 2 espacios; camelCase; componentes en PascalCase.
- Aliases: usar `@shared/*` y `@/*` (mapeados en `tsconfig.json` y `vite.config.ts`).

## Testing Guidelines
- Backend: `pytest -q` (si hay tests).
- Frontends: preferir Vitest/RTL si están configurados; pruebas unitarias cerca del código.
- Ejecuta `npm run typecheck` en `apps/admin` y `apps/tenant` antes de subir cambios.

## Commit & Pull Request Guidelines
- Commits pequeños y descriptivos: `feat(admin): agrega rutas de configuración`.
- PRs con: descripción, pasos de prueba, capturas si aplica, notas de migración.
- No modificar configuración global salvo necesidad justificada.

## Security & Configuration Tips
- Variables en `.env` (no subir secretos). CORS/CSRF según puertos locales.
- Compose construye admin/tenant desde la raíz para resolver `apps/packages/*`.

## Agent-Specific Instructions
- Cambios mínimos; respeta patrones, aliases y estructura monorepo.
- Reutiliza `@shared/{http,endpoints,domain,ui}` para servicios y UI.
- Usa `scripts/init.*` para levantar, compilar y revisar logs rápidamente.
