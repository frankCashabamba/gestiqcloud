# Revision Scaffold

This directory is kept only as revision scaffolding.

## Current Status

- `apps/backend/revision_scaffold/versions` is intentionally allowed to stay empty.
- The project does not use Python revision files as the primary migration source.
- The active migration workflow lives in `ops/migrations/` and `ops/scripts/migrate_all_migrations_idempotent.py`.

## Operational Rule

If there are no revision files under `revision_scaffold/versions`, the backend should treat the revision scaffold as disabled and skip `upgrade head`.

## Source Of Truth

- Schema changes: `ops/migrations/`
- SQL runner: `ops/scripts/migrate_all_migrations_idempotent.py`
