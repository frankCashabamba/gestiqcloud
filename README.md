# GestiQCloud - ERP/CRM Multi-Tenant

Sistema ERP/CRM multi-tenant para Espana y Ecuador.

## Estado
- En refactor y re-documentacion activa.

## Arranque rapido (local)
Requisitos:
- Python 3.11 + venv
- PostgreSQL
- Node 18+

Comando (Windows, PowerShell):
```powershell
scripts/start_local.ps1
```

Servicios por defecto:
- Backend: http://localhost:8000
- Admin: http://localhost:8081
- Tenant: http://localhost:8082

## Estructura principal
- `apps/backend` (FastAPI + SQLAlchemy + Alembic) - ver `apps/backend/README.md`
- `apps/admin` (React + Vite) - ver `apps/admin/README.md`
- `apps/tenant` (React + Vite, PWA) - ver `apps/tenant/README.md`
- `apps/packages` (paquetes compartidos) - ver `apps/packages/README.md`
- `ops` (infra y migraciones) - ver `ops/README.md`
- `workers` (workers/edge) - ver `workers/README.md`

## Migraciones y base de datos
- Alembic: `apps/backend/alembic/`
- SQL sueltas: `ops/migrations/`

Ejecutar migraciones idempotentes:
```powershell
python ops/scripts/migrate_all_migrations_idempotent.py
```

## Documentacion
Indice principal:
- `docs/README.md`

Historial y reportes archivados:
- `docs/legacy/root-archive-2026-02-18`
- `docs/legacy/module-archive-2026-02-18`
