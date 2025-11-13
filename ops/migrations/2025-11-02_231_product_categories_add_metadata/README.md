Title: Add category_metadata to product_categories

Context
- The ORM model `apps/backend/app/models/core/product_category.py` expects a JSONB column named `category_metadata`.
- The baseline migration `2025-11-01_000_baseline_modern/up.sql` creates `product_categories` without this column.
- At runtime, queries referencing `product_categories.category_metadata` fail with `psycopg2.errors.UndefinedColumn`.

What this migration does
- Adds the missing `category_metadata JSONB` column (idempotent).
- Adds an index on `name` used for ordering/filtering.

Apply
- This directory is auto‑applied by `scripts/py/bootstrap_imports.py` and the Admin UI Migrate button.

