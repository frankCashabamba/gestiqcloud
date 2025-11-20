DB?=$(DATABASE_URL)

.PHONY: migrate rls api worker front-admin front-tenant fmt lint test

migrate:
	psql "$(DB)" -v ON_ERROR_STOP=1 -f ops/migrations/apply.sql

rls:
	DATABASE_URL="$(DB)" python scripts/py/apply_rls.py --schema public --set-default

api:
	uvicorn apps.backend.prod:app --host 0.0.0.0 --port 8000

worker:
	celery -A apps.backend.celery_app worker -Q sri,sii -l info

front-admin front-tenant:
	npm run --prefix apps/$(@:front-%=%) dev

fmt:
	python -m black apps/backend || true

lint:
	python -m pyflakes apps/backend || true

test:
	pytest -q || true
