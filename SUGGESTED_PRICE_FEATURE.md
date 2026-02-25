# Feature: Precio Sugerido desde Receta

## Descripción

Esta funcionalidad permite que los productos con receta asociada tengan un **precio sugerido** calculado automáticamente basado en el costo de ingredientes. El usuario puede opcionalmente usar este precio como precio de venta.

## Cambios Realizados

### 1. Backend - Modelo de Datos

#### `apps/backend/app/models/core/products.py`
- Agregado: `suggested_price: float | None` - Precio sugerido calculado desde receta
- Agregado: `use_suggested_price: bool` - Flag para usar precio sugerido como precio de venta

### 2. Backend - Lógica de Cálculo

#### `apps/backend/app/services/recipe_calculator.py`
- Actualizada función `calculate_recipe_cost()` con:
  - Parámetro `update_product_price: bool = True`
  - Cálculo de precio sugerido: `unit_cost * 2` (Markup 100% = Margen 50%)
  - Sincronización automática con el producto si tiene receta asociada
  - Si `use_suggested_price=True`, actualiza el precio de venta

### 3. Backend - Schemas Pydantic

#### `apps/backend/app/modules/products/interface/http/tenant.py`
- `ProductCreate`: Agregados `suggested_price` y `use_suggested_price`
- `ProductUpdate`: Agregados `suggested_price` y `use_suggested_price`
- `ProductOut`: Retorna los nuevos campos
- `_to_product_out_row()`: Mapea correctamente los valores

### 4. Backend - Endpoints

#### `apps/backend/app/modules/production/interface/http/tenant.py`
- Nuevo endpoint: `POST /recipes/{recipe_id}/sync-product-price`
  - Sincroniza manualmente el precio sugerido del producto
  - Retorna: `suggested_price`, `unit_cost`, mensaje de confirmación

### 5. Frontend - UI de Productos

#### `apps/tenant/src/modules/products/Form.tsx`
- Nueva sección: "Precio Sugerido desde Receta"
- Muestra el precio sugerido (readonly)
- Checkbox: "Usar Precio Sugerido"
  - Si se marca, actualiza automáticamente el precio de venta
  - Solo visible si hay precio sugerido disponible

## Flujo de Uso

### Crear/Editar Receta
1. Usuario crea una receta para un producto
2. Agrega ingredientes con costos
3. El sistema calcula automáticamente el costo unitario
4. `calculate_recipe_cost()` calcula `suggested_price = unit_cost * 2`
5. El `suggested_price` se almacena en el producto

### Ver Producto
1. En el formulario de edición del producto
2. Sección "Precio Sugerido desde Receta" muestra:
   - Precio sugerido (calculado)
   - Checkbox para usar este precio

### Aplicar Precio Sugerido
**Opción 1: Desde formulario del producto**
1. Marcar checkbox "Usar Precio Sugerido"
2. El campo de precio se actualiza automáticamente
3. Guardar cambios

**Opción 2: API**
```bash
POST /api/v1/tenant/recipes/{recipe_id}/sync-product-price
```
Respuesta:
```json
{
  "success": true,
  "recipe_id": "uuid",
  "suggested_price": 0.13,
  "unit_cost": 0.066,
  "message": "Precio sugerido sincronizado con el producto"
}
```

## Ejemplo: PAN TAPADO

### Datos
- Costo total de ingredientes: $14.18
- Rendimiento: 216 unidades
- Costo por unidad: $14.18 / 216 = $0.066

### Precio Sugerido
```
Precio Sugerido = $0.066 * 2 = $0.13
Markup: 100%
Margen: 50%
```

### En el Formulario
```
Precio Sugerido: 0.13 $ [Calculado automáticamente desde receta]
☐ Usar Precio Sugerido   (Aplicar precio sugerido como precio de venta)
```

Si marca el checkbox:
- El campo "Precio (en tu moneda)" se actualiza a 0.13
- Al guardar, el producto usa este precio

## Migración de Base de Datos

La migración está en: `ops/migrations/2026-02-21_000_add_suggested_price_to_products/`

**Archivos:**
- `up.sql` - Crear columnas
- `down.sql` - Revertir cambios

**Ejecutar migración:**
```bash
# Tu sistema de migración personalizado
./apply_migration.sh 2026-02-21_000_add_suggested_price_to_products
```

**Cambios en BD:**
```sql
-- Agregar columnas
ALTER TABLE products
ADD COLUMN suggested_price NUMERIC(12, 2) NULL,
ADD COLUMN use_suggested_price BOOLEAN DEFAULT FALSE;
```

## Consideraciones

1. **Actualización Automática**: Cuando se modifica una receta, el precio sugerido se recalcula automáticamente
2. **No Forzado**: El usuario puede mantener un precio diferente al sugerido
3. **Flexibilidad**: El flag `use_suggested_price` permite cambiar entre usar precio sugerido y precio manual
4. **Margen Fijo**: El markup de 100% (margen 50%) es estándar, pero puede ajustarse en `recipe_calculator.py`

## Archivos Modificados

- `apps/backend/app/models/core/products.py`
- `apps/backend/app/services/recipe_calculator.py`
- `apps/backend/app/modules/products/interface/http/tenant.py`
- `apps/backend/app/modules/production/interface/http/tenant.py`
- `apps/tenant/src/modules/products/Form.tsx`

## Testing

Para verificar:

1. Crear un producto con receta
2. Agregar ingredientes con costos
3. Verificar que `suggested_price` se calcula correctamente
4. Marcar "Usar Precio Sugerido"
5. Guardar y verificar que `price` se actualiza
6. Modificar ingredientes y verificar recálculo
