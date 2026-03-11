# Migration: Seed Business Categories

**Date:** November 29, 2025  
**Purpose:** Seed example rows into `business_categories`

---

## What It Does

Adds six business categories to the database:
- `retail` - Retail / Store
- `services` - Services
- `manufacturing` - Manufacturing
- `food_beverage` - Food and Beverage
- `healthcare` - Healthcare
- `education` - Education

## Why It Exists

This migration was part of the hardcoding removal effort:
- Before: categories were hardcoded in frontend and backend code.
- After: categories are loaded dynamically from the database through `/api/v1/business-categories`.

## Related Files

- `apps/backend/app/routers/business_categories.py`: business categories router
- `apps/backend/app/platform/http/router.py`: router registration
- This was step 1 of the hardcoding removal work

## Execution

This repository does not rely on Alembic for `ops/migrations`.
Use the SQL migration runner instead.

```bash
python ops/scripts/migrate_all_migrations_idempotent.py
```

## Verification

```bash
psql -U postgres -d gestiqcloud -c "SELECT code, name FROM business_categories;"
```

## Rollback

Rollback depends on your local workflow and the availability of `down.sql`.
If you need to revert manually, inspect the migration folder and apply the matching rollback SQL.
*** Add File: ops/migrations/README.md
# SQL Migrations

This directory contains the repository's manual SQL migration set.

## Important

- These migrations are not Alembic revisions.
- They are applied by the custom SQL runners in `ops/scripts/`.
- Folder names must be in English.
- Comments, README files, and migration notes should be written in English.
- If a table or column already exists in Spanish because the application depends on it, do not rename it casually. Treat that as a schema refactor, not a documentation cleanup.

## Layout

Each migration normally lives in its own folder:

```text
YYYY-MM-DD_NNN_description/
  up.sql
  down.sql        # optional
  README.md       # optional
```

Standalone `.sql` files may still exist for older historical cases, but new work should prefer the folder layout above.

## Naming Convention

- Use a sortable date prefix: `YYYY-MM-DD`.
- Use a sequence slot after the date, for example `_000`, `_001`, `_010`.
- Use a short English slug describing the change.
- Example: `2026-03-07_000_widen_detected_ruc`

## Applying Migrations

Use the idempotent runner:

```bash
python ops/scripts/migrate_all_migrations_idempotent.py
```

It reads `DATABASE_URL`, applies folders in order, and records applied entries in `_migrations`.

## Authoring Rules

- Prefer idempotent SQL where possible.
- Keep `up.sql` safe to run once in a real environment.
- Add `down.sql` only when rollback is practical and well understood.
- Keep comments short and operational.
- Avoid mixing schema refactors with data cleanup unless the coupling is intentional and documented.

## Before Changing Old Migrations

- If the migration has already been applied in a live or shared database, renaming folders or changing tracked names requires database cleanup or re-alignment.
- For local-only cleanup, you may update `_migrations` accordingly.
- For shared environments, treat migration renames as operational changes and coordinate them first.

## Recommended Verification

- Check the target objects exist after `up.sql`.
- Confirm `_migrations` contains the expected folder name.
- Run the application path that depends on the changed schema.
