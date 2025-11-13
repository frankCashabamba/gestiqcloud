-- Revertir a columna sin conversión de unidades
ALTER TABLE recipe_ingredients DROP COLUMN IF EXISTS costo_ingrediente;

ALTER TABLE recipe_ingredients
ADD COLUMN costo_ingrediente NUMERIC(12,4)
GENERATED ALWAYS AS (
    CASE
        WHEN qty_presentacion > 0 THEN (qty * costo_presentacion) / qty_presentacion
        ELSE 0
    END
) STORED;

-- Eliminar función de conversión
DROP FUNCTION IF EXISTS convert_to_base_unit(NUMERIC, TEXT, TEXT);
