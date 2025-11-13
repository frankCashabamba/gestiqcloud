# Migración: Columnas calculadas para recetas

**Fecha**: 2025-11-03
**Tipo**: Schema change

## Descripción

Agrega columnas calculadas (GENERATED) para cálculos automáticos de costos:

1. **recipes.costo_por_unidad**: Columna generada que calcula automáticamente `costo_total / rendimiento`
2. **recipe_ingredients.costo_ingrediente**: Columna generada que calcula `(qty * costo_presentacion) / qty_presentacion`

## Cambios

### UP
- Agrega `costo_por_unidad NUMERIC(12,4)` a `recipes` como columna GENERATED STORED
- Agrega `costo_ingrediente NUMERIC(12,4)` a `recipe_ingredients` como columna GENERATED STORED
- Crea índice `idx_recipes_costo_por_unidad`

### DOWN
- Elimina columnas y índice

## Impacto

- ✅ Sin downtime
- ✅ Los valores se calculan automáticamente al INSERT/UPDATE
- ✅ Mejora rendimiento al evitar cálculos en queries
- ✅ Consistencia garantizada por PostgreSQL

## Testing

```sql
-- Verificar cálculo automático
SELECT id, name, costo_total, rendimiento, costo_por_unidad 
FROM recipes 
LIMIT 5;

-- Verificar ingredientes
SELECT id, qty, costo_presentacion, qty_presentacion, costo_ingrediente
FROM recipe_ingredients
LIMIT 5;
```
