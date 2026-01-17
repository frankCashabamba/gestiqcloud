# GestiQCloud - ERP/CRM Multi-Tenant

Sistema ERP/CRM multi-tenant para España y Ecuador.

**Estado actual:** En refactor y re-documentación (nov 2025). Las notas de “FASES 1-6 100%” ya no aplican.

---

## 🚀 Arranque rápido (local)
- Requisitos: Python 3.11 + venv, PostgreSQL, Node 18+.
- Comando (Windows, PowerShell):
  ```powershell
  scripts/start_local.ps1
  ```
  Servicios por defecto: Backend http://localhost:8000, Admin http://localhost:8081, Tenant http://localhost:8082.
- Si 8000 está ocupado: `uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload`.

## 📁 Estructura principal
- `apps/backend` (FastAPI + SQLAlchemy + Alembic) — ver `apps/backend/README.md`.
- `apps/admin` (React + Vite) — ver `apps/admin/README.md`.
- `apps/tenant` (React + Vite, PWA) — ver `apps/tenant/README.md`.
- `apps/packages` (ui/shared/etc.) — ver `apps/packages/README.md`.
- `ops` (infra, migraciones SQL, scripts) — ver `ops/README.md`.
- `workers` (edge workers) — ver `workers/README.md`.

## 🗃️ Migraciones y base de datos
- Alembic: `apps/backend/alembic/`.
- SQL sueltas: `ops/migrations/`.
- Ejecutar migraciones idempotentes:
  ```powershell
  python ops/scripts/migrate_all_migrations_idempotent.py
  ```
  Ajusta `DATABASE_URL` en `.env` del backend.

## 🔧 Backend (dev)
```powershell
cd apps/backend
# activar venv y deps instaladas
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pytest
```

## 🎨 Frontend
Admin:
```powershell
cd apps/admin
npm install
npm run dev -- --host --port 8081
```
Tenant:
```powershell
cd apps/tenant
npm install
npm run dev -- --host --port 8082
```

## 📌 Notas y mantenimiento
- Limpiar caches: `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`, `__pycache__/`.
- Scripts de ops: backups, migraciones, clamav en `ops/scripts/` (detalles en `ops/README.md`).
- Troubleshooting: puertos ocupados → `netstat -ano | findstr :8000` y `taskkill /PID <PID> /F`.

## 📚 Documentación

### ⭐ Important - Configuration & Security
- **[ANALISIS_HARDCODEOS.md](ANALISIS_HARDCODEOS.md)** - Hardcodeos y configuración (⭐ READ THIS)
- **[HARDCODEOS_README.md](HARDCODEOS_README.md)** - Índice de documentación sobre hardcodeos
- [.env.example](.env.example) - Variables de entorno requeridas

### System Architecture
- docs/arquitectura.md
- docs/dev-experience.md
- docs/seguridad.md
- docs/backend.md
- docs/datos-migraciones.md
- docs/runbooks/README.md
- docs/deploy.md

### API & Examples
- docs/examples-curl.md
- docs/payments-einvoicing.md
- docs/observabilidad.md
- docs/entornos.md
- docs/adr/README.md
- docs/frontend-structure.md
- docs/frontend-commands.md
- docs/release-checklist.md
- docs/api-contracts.md
- docs/cache-uploads.md

### Modules
- apps/backend/README.md
- apps/backend/alembic/README.md
- apps/admin/README.md
- apps/tenant/README.md
- apps/packages/README.md
- ops/README.md
- importacion/README.md
