# Fullstack Docker — FastAPI + Admin & Tenant (React+Vite+Nginx)

Servicios:
- **db**: Postgres 15 (puerto 5432)
- **backend**: FastAPI en 8000
- **admin**: web en 8081 (Nginx estático + proxy `/api` → backend)
- **tenant**: web en 8082 (igual)

## Uso rápido
```bash
cp backend/.env.example backend/.env
docker compose build
docker compose up
```

Admin → http://localhost:8081  
Tenant → http://localhost:8082  
API → http://localhost:8000/docs

> Los front llaman a `/api/...` (Nginx proxy), por lo que no necesitas CORS desde UI.
> Si accedes a la API desde otros orígenes, configura `CORS_ORIGINS` en `backend/.env`.

## Healthchecks
- `GET /health`: estado básico del backend.
- `GET /health/redis`: si `REDIS_URL` está configurado, realiza `PING` y devuelve `{ enabled, ok }` (503 si falla). Si no está configurado, responde `{ enabled: false, ok: true }`.
