# GestiQCloud (monorepo ERP/CRM)

Estado: en refactor y re-documentación (nov 2025). Las notas antiguas de fases “100%” ya no aplican.

## 🚀 Quick Start (local)
```bash
# 1. Levantar stack (ejemplo simple)
docker compose up -d
```
- Backend: http://localhost:8000
- Frontend Tenant: http://localhost:8082
- Frontend Admin: http://localhost:8081

## 📁 Estructura
- `apps/backend`: FastAPI + SQLAlchemy (Py 3.11). Alembic en `apps/backend/alembic/`.
- `apps/admin`: React + Vite (npm).
- `apps/tenant`: React + Vite (npm).
- `packages/`: libs compartidas (ui/shared).
- `ops/`: infra y migraciones SQL (`ops/migrations/`), scripts en `ops/scripts/`.
- `scripts/`, `workers/`, `docs/`: utilidades, workers, documentación.

## 🛠 Requisitos
- Python 3.11 + pip/venv.
- Node.js 18+ y npm.
- PostgreSQL (config en `.env.local` de backend).

## Backend (dev)
```bash
cd apps/backend
python -m venv .venv
# Win: .venv\Scripts\activate   |  Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
cp .env.local .env   # revisa credenciales DB
uvicorn app.main:app --reload
```
API: http://localhost:8000

## Frontend Admin
```bash
cd apps/admin
npm install
npm run dev -- --host --port 8081
```

## Frontend Tenant
```bash
cd apps/tenant
npm install
npm run dev -- --host --port 8082
```

## Base de datos y migraciones
- Alembic: `apps/backend/alembic`.
- SQL sueltas: `ops/migrations/`.
- Ejecución idempotente que usas:
  ```powershell
  python ops/scripts/migrate_all_migrations_idempotent.py
  ```
- Ajusta `DATABASE_URL` en `.env`.

## Tests backend
```bash
cd apps/backend
pytest
```

## Pendiente
- Reescribir documentación funcional y de despliegue.
- Validar migraciones SQL/Alembic vigentes antes de producción.
- Completar guías de CI/CD en `ops/` y `scripts/`.
