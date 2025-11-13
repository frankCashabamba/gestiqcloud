Compose Profiles
================

Profiles
- web: Admin + Tenant PWAs
- worker: Redis + Celery worker
- migrate: One-off migrations service

Usage
- Full local (with docker-compose.override.yml):
  - docker compose up -d --build
- Only backend + DB (compose-min):
  - scripts/init.ps1 compose-min
- Web only:
  - docker compose --profile web up -d admin tenant
  - or scripts/init.ps1 compose-web
- Worker only:
  - docker compose --profile worker up -d redis celery-worker
  - or scripts/init.ps1 compose-worker
- Migrate one-off:
  - docker compose --profile migrate run --rm migrations
  - or scripts/init.ps1 compose-migrate

Env
- Root .env (for compose interpolation): see .env.example
- Backend specific env: apps/backend/.env.example
