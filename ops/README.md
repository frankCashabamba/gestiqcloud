# Operaciones / Infra

Infraestructura, migraciones SQL y scripts de soporte para despliegue y mantenimiento.

## Estructura
- `ci/`: utilidades para pipelines (checks, migrate helpers).
- `dns/`: configuraciones DNS (Cloudflare) y registros.
- `migrations/`: migraciones SQL manuales (snapshot consolidado en `2025-11-21_000_complete_consolidated_schema`).
- `scripts/`: automatizaciones (migraciones idempotentes, generación de SQL, checks de endpoints).
- `systemd/`: unidades de servicio (ej. `gestiq-worker-imports.service`).
- `requirements.txt`: dependencias para scripts.

## Pipelines CI/CD
- `.github/workflows/ci.yml`: detecta cambios frontend/backend y ejecuta:
  - Backend: instala deps, recrea `test.db`, `Base.metadata.create_all`, pytest, `ops/scripts/check_endpoints.py`.
  - Frontend: `npm ci`/`npm install`, `npm run typecheck`, `npm run build` para admin y tenant.

## Scripts clave (`ops/scripts`)
- `migrate_all_migrations_idempotent.py`: aplica migraciones SQL en orden, saltando las ya aplicadas (requiere `DATABASE_URL`).
- `migrate_all_migrations.py`: versión simple no idempotente.
- `generate_migration_from_models.py`: genera SQL desde modelos actuales para comparar con DB.
- `check_endpoints.py`: smoke test de endpoints FE/BE (usado en CI backend).

## Migraciones SQL
- `migrations/2025-11-21_000_complete_consolidated_schema/`: snapshot completo con `up.sql`/`down.sql` y README descriptivo.
- Usar los scripts anteriores para aplicarlas; tomar backups previos (`pg_dump`).

## DNS y despliegues
- `dns/*.txt`: registros Cloudflare para dominios `gestiqcloud.com` y subdominios.
- Despliegue de API en Render (ver `render.yaml` en raíz). Worker en Cloudflare (ver `workers/README.md`).

## Systemd / servicios
- Unidades ejemplo para workers (imports). Ajustar rutas/env antes de desplegar en servidores.

## Backups y seguridad
- Respaldar DB antes de migraciones manuales.
- Manejar secretos vía variables de entorno (no commitear `.env`).
- Revisar dominios permitidos en CORS/worker antes de exponer endpoints.

## Pendientes
- Documentar pipeline de despliegue a Render/Cloudflare con pasos exactos.
- Añadir checklist post-migración.
