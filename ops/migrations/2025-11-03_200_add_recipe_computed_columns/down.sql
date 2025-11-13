-- Eliminar columna costo_por_unidad de recipes
DROP INDEX IF EXISTS idx_recipes_costo_por_unidad;
ALTER TABLE recipes DROP COLUMN IF EXISTS costo_por_unidad;

-- Eliminar columna costo_ingrediente de recipe_ingredients
ALTER TABLE recipe_ingredients DROP COLUMN IF EXISTS costo_ingrediente;
