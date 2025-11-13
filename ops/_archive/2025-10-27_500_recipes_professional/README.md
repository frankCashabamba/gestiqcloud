# Migración: Sistema de Recetas Profesional

**Fecha**: 2025-10-27  
**Versión**: 500

## Descripción

Sistema completo de gestión de recetas para producción (panaderías, restaurantes, manufactura).

### Características

- **Recetas con rendimiento**: Define cuántas unidades produce cada receta
- **Ingredientes con info de compra**: Presentación comercial (saco 110 lb, caja 24 uds)
- **Cálculo automático de costos**: Trigger que actualiza costo total y unitario
- **Escalado de producción**: Calcula materiales para producir X unidades
- **Multi-tenant con RLS**: Aislamiento por tenant_id
- **Funciones PostgreSQL**: `calculate_recipe_cost()`, `calculate_production_materials()`

## Tablas

### `recipes`
- Receta principal con rendimiento (144 panes)
- Costo total y costo por unidad (generado automáticamente)
- Tiempo de preparación e instrucciones

### `recipe_ingredients`
- Ingredientes de la receta
- Información de compra: presentación, cantidad, costo
- Costo calculado automáticamente: `qty × (costo_presentacion / qty_presentacion)`

## Ejemplo de Uso

```sql
-- Crear receta de Pan Tapado (rendimiento 144 unidades)
INSERT INTO recipes (tenant_id, product_id, nombre, rendimiento, instrucciones)
VALUES (
  '123e4567-e89b-12d3-a456-426614174000',
  '223e4567-e89b-12d3-a456-426614174000',
  'Pan Tapado',
  144,
  'Mezclar ingredientes secos. Agregar líquidos...'
);

-- Agregar ingrediente: Harina (110 lb en saco de $35)
INSERT INTO recipe_ingredients (
  recipe_id, producto_id, qty, unidad_medida,
  presentacion_compra, qty_presentacion, unidad_presentacion, costo_presentacion
) VALUES (
  recipe_id_generado,
  producto_harina_id,
  50, 'lb',
  'Saco 110 lbs', 110, 'lb', 35.00
);
-- Costo ingrediente = 50 × (35 / 110) = $15.91

-- Calcular producción para 1000 panes
SELECT * FROM calculate_production_materials(recipe_id, 1000);
```

## Dependencias

- Tabla `tenants` (tenant_id UUID)
- Tabla `products` (producto_id UUID)
- Función `update_updated_at()` (debe existir previamente)

## Aplicar Migración

```bash
python scripts/py/bootstrap_imports.py --dir ops/migrations/2025-10-27_500_recipes_professional
```

## Rollback

```bash
psql -f ops/migrations/2025-10-27_500_recipes_professional/down.sql
```
