.PHONY: b.setup b.lint b.format b.test b.all
.PHONY: d.up d.down d.down.v d.build d.rebuild.backend d.logs d.ps d.restart.backend d.exec.backend

# Install backend dependencies into current environment
b.setup:
	python -m pip install -r backend/requirements.txt

# Run Ruff (lint) with autofix
b.lint:
	ruff check backend/app --fix

# Run isort and black formatting on backend
b.format:
	isort backend/app
	black backend/app

# Run backend test suite (uses SQLite in-memory via conftest)
b.test:
	pytest -q backend/app/test -o cache_dir=/tmp/pytest_cache

# Convenience: lint + format + tests
b.all: b.lint b.format b.test

# -------------------- Docker Compose helpers --------------------
S ?= backend

# Bring up all services (detached)
d.up:
	docker compose up -d

# Build all images
d.build:
	docker compose build

# Rebuild and restart only backend service
d.rebuild.backend:
	docker compose build backend && docker compose up -d backend

# Follow logs (use: make d.logs S=backend)
d.logs:
	docker compose logs -f $(S)

# Show compose status
d.ps:
	docker compose ps

# Restart backend service
d.restart.backend:
	docker compose restart backend

# Exec into backend container (bash)
d.exec.backend:
	docker compose exec backend bash

# Stop and remove containers
d.down:
	docker compose down

# Stop, remove containers and volumes
d.down.v:
	docker compose down -v
