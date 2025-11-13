-- Función para convertir unidades a gramos/mililitros base
CREATE OR REPLACE FUNCTION convert_to_base_unit(
    qty NUMERIC,
    unit_from TEXT,
    unit_to TEXT
) RETURNS NUMERIC AS $$
DECLARE
    qty_in_grams NUMERIC;
    result NUMERIC;
BEGIN
    -- Si las unidades son iguales, retornar cantidad original
    IF LOWER(unit_from) = LOWER(unit_to) THEN
        RETURN qty;
    END IF;
    
    -- Convertir desde unidad_from a gramos (peso) o ml (volumen)
    CASE LOWER(unit_from)
        -- Peso
        WHEN 'kg' THEN qty_in_grams := qty * 1000;
        WHEN 'g' THEN qty_in_grams := qty;
        WHEN 'lb' THEN qty_in_grams := qty * 453.592;
        WHEN 'oz' THEN qty_in_grams := qty * 28.3495;
        WHEN 'mg' THEN qty_in_grams := qty / 1000;
        WHEN 'ton' THEN qty_in_grams := qty * 1000000;
        
        -- Volumen (usar ml como base)
        WHEN 'l' THEN qty_in_grams := qty * 1000;
        WHEN 'ml' THEN qty_in_grams := qty;
        WHEN 'gal' THEN qty_in_grams := qty * 3785.41;
        WHEN 'qt' THEN qty_in_grams := qty * 946.353;
        WHEN 'pt' THEN qty_in_grams := qty * 473.176;
        WHEN 'cup' THEN qty_in_grams := qty * 236.588;
        WHEN 'fl_oz' THEN qty_in_grams := qty * 29.5735;
        WHEN 'tbsp' THEN qty_in_grams := qty * 14.7868;
        WHEN 'tsp' THEN qty_in_grams := qty * 4.92892;
        
        -- Unidades (sin conversión)
        WHEN 'unit', 'unidades', 'uds', 'pcs' THEN qty_in_grams := qty;
        
        ELSE qty_in_grams := qty; -- Si no se reconoce, asumir misma unidad
    END CASE;
    
    -- Convertir de gramos/ml a unidad_to
    CASE LOWER(unit_to)
        -- Peso
        WHEN 'kg' THEN result := qty_in_grams / 1000;
        WHEN 'g' THEN result := qty_in_grams;
        WHEN 'lb' THEN result := qty_in_grams / 453.592;
        WHEN 'oz' THEN result := qty_in_grams / 28.3495;
        WHEN 'mg' THEN result := qty_in_grams * 1000;
        WHEN 'ton' THEN result := qty_in_grams / 1000000;
        
        -- Volumen
        WHEN 'l' THEN result := qty_in_grams / 1000;
        WHEN 'ml' THEN result := qty_in_grams;
        WHEN 'gal' THEN result := qty_in_grams / 3785.41;
        WHEN 'qt' THEN result := qty_in_grams / 946.353;
        WHEN 'pt' THEN result := qty_in_grams / 473.176;
        WHEN 'cup' THEN result := qty_in_grams / 236.588;
        WHEN 'fl_oz' THEN result := qty_in_grams / 29.5735;
        WHEN 'tbsp' THEN result := qty_in_grams / 14.7868;
        WHEN 'tsp' THEN result := qty_in_grams / 4.92892;
        
        -- Unidades
        WHEN 'unit', 'unidades', 'uds', 'pcs' THEN result := qty_in_grams;
        
        ELSE result := qty_in_grams; -- Si no se reconoce, retornar base
    END CASE;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Eliminar columna generada actual
ALTER TABLE recipe_ingredients DROP COLUMN IF EXISTS costo_ingrediente;

-- Recrear columna con conversión de unidades
ALTER TABLE recipe_ingredients 
ADD COLUMN costo_ingrediente NUMERIC(12,4) 
GENERATED ALWAYS AS (
    CASE 
        WHEN qty_presentacion > 0 THEN 
            (convert_to_base_unit(qty, unidad_medida, unidad_presentacion) / qty_presentacion) * costo_presentacion
        ELSE 0 
    END
) STORED;

COMMENT ON COLUMN recipe_ingredients.costo_ingrediente IS 'Costo calculado del ingrediente con conversión automática de unidades';

COMMENT ON FUNCTION convert_to_base_unit IS 'Convierte cantidades entre diferentes unidades de medida';
