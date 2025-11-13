# 2025-11-03_050_create_recipes_tables

Creates the core `recipes` and `recipe_ingredients` tables so later migrations (computed columns, production orders, etc.) have the required base schema.

## Deploy notes

1. Run the migration with the standard `scripts/init.ps1 local` helper.
2. No data backfill is required because the tables are new.

## Rollback plan

Execute `down.sql` to drop the tables and associated RLS policies (this will delete any stored recipes/ingredients).
