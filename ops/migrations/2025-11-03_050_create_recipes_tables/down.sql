-- Down migration for 2025-11-03_050_create_recipes_tables

DROP POLICY IF EXISTS tenant_isolation_recipe_ingredients ON recipe_ingredients;
DROP POLICY IF EXISTS tenant_isolation_recipes ON recipes;

DROP TABLE IF EXISTS recipe_ingredients;
DROP TABLE IF EXISTS recipes;
