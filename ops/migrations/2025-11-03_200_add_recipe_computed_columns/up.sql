-- Agregar columna calculada costo_por_unidad en recipes
ALTER TABLE recipes 
ADD COLUMN costo_por_unidad NUMERIC(12,4) 
GENERATED ALWAYS AS (
  CASE 
    WHEN rendimiento > 0 THEN costo_total / rendimiento 
    ELSE 0 
  END
) STORED;

-- Agregar columna calculada costo_ingrediente en recipe_ingredients
ALTER TABLE recipe_ingredients 
ADD COLUMN costo_ingrediente NUMERIC(12,4) 
GENERATED ALWAYS AS (
  CASE 
    WHEN qty_presentacion > 0 THEN (qty * costo_presentacion) / qty_presentacion
    ELSE 0 
  END
) STORED;

-- Crear índice en costo_por_unidad para búsquedas
CREATE INDEX idx_recipes_costo_por_unidad ON recipes(costo_por_unidad);
