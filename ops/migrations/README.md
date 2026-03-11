# SQL Migrations

This directory contains the project's manual SQL migration set.

## Important

- These entries are not backend revision-scaffold entries.
- They are executed by the custom SQL runners under `ops/scripts/`.
- Migration folder names must stay in English.
- Comments, notes, and README files in this directory should also stay in English.
- If a schema object already uses Spanish because application code depends on it, do not rename it as part of a cosmetic cleanup. Treat that as a proper schema refactor.

## Standard Layout

Most migrations should use this structure:

```text
YYYY-MM-DD_NNN_description/
  up.sql
  down.sql        # optional
  README.md       # optional
```

Older standalone `.sql` files may still exist for historical reasons, but new migrations should use the folder layout above.

## Naming Rules

- Use a sortable date prefix: `YYYY-MM-DD`
- Use a numeric slot after the date: `_000`, `_001`, `_010`, etc.
- Use a short English slug that describes the change
- Example: `2026-03-07_000_widen_detected_ruc`

## Applying Migrations

Use the idempotent SQL runner:

```bash
python ops/scripts/migrate_all_migrations_idempotent.py
```

The runner reads `DATABASE_URL`, applies migrations in order, and records applied folder names in `_migrations`.

## Authoring Guidelines

- Prefer idempotent SQL where practical.
- Keep migration comments short and operational.
- Add `down.sql` only when rollback is realistic and understood.
- Avoid mixing unrelated schema and data changes in the same migration unless the coupling is intentional.

## Operational Notes

- Renaming an already applied migration folder changes its tracked identity in `_migrations`.
- In local-only environments you can realign `_migrations` manually.
- In shared environments, treat renames as an operational change and coordinate them first.
