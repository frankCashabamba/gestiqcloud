-- Rollback: 2026-02-22_002_recipe_steps_table

BEGIN;

DROP TABLE IF EXISTS recipe_steps;

COMMIT;
