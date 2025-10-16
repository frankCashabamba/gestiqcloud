# Migration Notes: JWT Unification on PyJWT

## Environment Variables
Set these in non-dev environments (dev/test have safe defaults):

- `JWT_SECRET` (or legacy `JWT_SECRET_KEY`)
- `JWT_ALGORITHM` (default `HS256`)
- `ACCESS_TTL_MINUTES` (or legacy `ACCESS_TOKEN_EXPIRE_MINUTES`)
- `REFRESH_TTL_DAYS` (or legacy `REFRESH_TOKEN_EXPIRE_DAYS`)

## API Compatibility
- Preferred:
  - Admin login: `POST /api/v1/admin/auth/login`
  - Tenant login: `POST /api/v1/tenant/auth/login`
- Legacy alias retained: `POST /api/v1/auth/login` (tenant-first, then admin)

## CSRF (Admin JSON APIs)
- If CSRF is enforced, the FE must include `X-CSRF-Token`.
- Use `GET /api/v1/admin/auth/csrf` to bootstrap and set `csrf_token` cookie in dev.

## Post-Deploy Smoke Checks
- Admin login, call `/api/v1/me/admin` with Bearer token.
- Tenant login, refresh rotation flow.
- Protected endpoints that depend on `Authorization: Bearer`.

## Notes
- `python-jose` removed; `PyJWT` retained.
- All JWT decode paths route through `JwtService`.
- Error handling standardized on `jwt.ExpiredSignatureError` and `jwt.InvalidTokenError`.

### Admin “Ejecutar migraciones” button

- Backend endpoint: `/v1/admin/ops/migrate` triggers a Render Job if configured.
- Required env on backend service:
  - `RENDER_API_KEY` (Render API key with Jobs access)
  - `RENDER_MIGRATE_JOB_ID` (ID of the Render Job that runs migrations)
  - Optional fallback: `ALLOW_INLINE_MIGRATIONS=1` to run Alembic + RLS inline (not recommended in prod).
- Status endpoint: `/v1/admin/ops/migrate/status`.
- Render Job command should include:
  - `alembic upgrade head`
  - `python ../scripts/py/apply_rls.py --schema public --set-default`
  - Any supplementary SQL now covered by Alembic (e.g., tenants bootstrap `a20005_tenants_bootstrap`).


## Tenancy Migrations (2025-10-09)

This section documents the multi-tenant bootstrap using UUID `tenant_id`, ordered steps, verification, and rollback guidance.

### Order of SQL migrations (ops/migrations)
- 2025-10-09_001_tenants
- 2025-10-09_010_add_tenant_uuid_products
- 2025-10-09_011_add_tenant_uuid_clients
- 2025-10-09_012_add_tenant_uuid_facturas
- 2025-10-09_013_add_tenant_uuid_payments
- 2025-10-09_014_add_tenant_uuid_bank_accounts
- 2025-10-09_015_add_tenant_uuid_bank_transactions
- 2025-10-09_016_add_tenant_uuid_import_batches
- 2025-10-09_017_add_tenant_uuid_import_item_corrections
- 2025-10-09_018_add_tenant_uuid_import_lineage
- 2025-10-09_019_add_tenant_uuid_import_mappings
- 2025-10-09_020_add_tenant_uuid_datos_importados
- 2025-10-09_021_add_tenant_uuid_internal_transfers
- 2025-10-09_022_add_tenant_uuid_modulos_empresamodulo
- 2025-10-09_023_add_tenant_uuid_modulos_moduloasignado
- 2025-10-09_024_add_tenant_uuid_core_configuracionempresa
- 2025-10-09_025_add_tenant_uuid_core_configuracioninventarioempresa
- 2025-10-09_026_add_tenant_uuid_core_perfilusuario
- 2025-10-09_027_add_tenant_uuid_core_rolempresa
- 2025-10-09_028_add_tenant_uuid_facturas_temp
- 2025-10-09_029_add_tenant_uuid_auditoria_importacion
- 2025-10-09_030_add_tenant_uuid_usuarios_usuariorolempresa

Note: legacy `empresa_id` is intentionally kept during transition. Drop in a later release once fully migrated.

### How it runs in Render
- Backend `render.yaml` sets:
  - `RUN_LEGACY_MIGRATIONS=1`
  - `RUN_RLS_APPLY=1`
  - `RLS_SCHEMAS=public`
  - `RLS_SET_DEFAULT=1`
- Entry `python prod.py` executes Alembic, then applies all folders with `up.sql`, then runs `scripts/py/apply_rls.py`.

### Manual apply (optional)
- Per folder:
  - `python scripts/py/apply_migration.py --dsn "$DATABASE_URL" --dir ops/migrations/<FOLDER> --action up`
- RLS:
  - `python scripts/py/apply_rls.py --schema public --set-default`

### Verification queries
- Tenants populated count:
  - `SELECT (SELECT count(*) FROM public.tenants) AS tenants, (SELECT count(*) FROM public.core_empresa) AS empresas;`
- Check a sample mapping:
  - `SELECT e.id AS empresa_id, t.id AS tenant_uuid, t.slug FROM public.core_empresa e JOIN public.tenants t ON t.empresa_id = e.id LIMIT 5;`
- Check tenant_id presence and FK (example products):
  - `\d+ public.products` (psql) should show `tenant_id uuid NOT NULL` and FK to `tenants(id)`, plus index `ix_products_tenant_id`.
- RLS enabled:
  - `SELECT relname FROM pg_class WHERE relrowsecurity;`
  - For each table with `tenant_id`, expect RLS enabled and policy `rls_tenant`.

### Rollback guidance (no down.sql provided)
- For emergency rollback on a specific table, do in one transaction:
  1) Drop policy and RLS if interfering (optional):
     - `ALTER TABLE public.<table> DISABLE ROW LEVEL SECURITY;`
  2) Drop FK and index:
     - `ALTER TABLE public.<table> DROP CONSTRAINT IF EXISTS fk_<table>_tenant;`
     - `DROP INDEX IF EXISTS ix_<table>_tenant_id;`
  3) Allow NULLs and drop the column if required:
     - `ALTER TABLE public.<table> ALTER COLUMN tenant_id DROP NOT NULL;`
     - `ALTER TABLE public.<table> DROP COLUMN IF EXISTS tenant_id;`
- Do not drop the `tenants` table unless all dependents are reverted first.

### Post-deploy smoke
- Make authenticated tenant request and confirm cross-tenant reads return empty.
- Verify cookies and CORS still work via `https://api.gestiqcloud.com`.
