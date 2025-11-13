# Migración: Conversión automática de unidades en recetas

**Fecha**: 2025-11-03
**Tipo**: Schema change + Function

## Descripción

Agrega conversión automática de unidades al calcular el costo de ingredientes en recetas.

**Problema**: Si la receta usa 85 gramos de sal pero compras en sacos de 50 libras, el cálculo estaba incorrecto.

**Solución**: Función `convert_to_base_unit()` que convierte automáticamente entre unidades.

## Ejemplo

### Antes (INCORRECTO):
```sql
Receta: 85 g
Compra: Saco 50 lb por $63.75
Cálculo: (85 / 50) × $63.75 = $108.38 ❌
```

### Después (CORRECTO):
```sql
Receta: 85 g
Compra: Saco 50 lb por $63.75
Conversión: 85 g → 0.187 lb
Cálculo: (0.187 / 50) × $63.75 = $0.24 ✅
```

## Unidades soportadas

### Peso
- kg, g, mg, ton
- lb (libras), oz (onzas)

### Volumen
- L, ml
- gal (galones), qt (cuartos), pt (pintas)
- cup, fl_oz, tbsp, tsp

### Conteo
- unit, unidades, uds, pcs

## Cambios

### UP
1. Crea función `convert_to_base_unit(qty, unit_from, unit_to)`
2. Elimina columna `costo_ingrediente` actual
3. Recrea con conversión automática

### DOWN
- Revierte a cálculo sin conversión
- Elimina función

## Testing

```sql
-- Test 1: Sal (g → lb)
SELECT convert_to_base_unit(85, 'g', 'lb'); -- 0.187 lb

-- Test 2: Harina (lb → kg)
SELECT convert_to_base_unit(10, 'lb', 'kg'); -- 4.536 kg

-- Test 3: Verificar costo calculado
SELECT 
    qty, unidad_medida,
    qty_presentacion, unidad_presentacion,
    costo_presentacion,
    costo_ingrediente
FROM recipe_ingredients
WHERE producto_id IN (
    SELECT id FROM products WHERE name = 'Sal'
);
```

## Impacto

- ✅ Cálculos correctos independientemente de unidades
- ✅ Sin necesidad de conversión manual
- ✅ Mejora precisión de costos
- ⚠️ Requiere recalcular recetas existentes
