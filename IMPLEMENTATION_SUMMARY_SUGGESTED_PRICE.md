# Resumen de Implementación: Precio Sugerido desde Receta

**Fecha**: 2026-02-21
**Feature**: Precio Sugerido desde Receta para Productos
**Estado**: ✅ Completado

---

## Descripción

Sistema automático que calcula un **precio de venta sugerido** basado en el costo total de ingredientes de una receta, con la fórmula:

```
Precio Sugerido = Costo Unitario × 2
(Markup 100% = Margen 50%)
```

---

## Archivos Modificados

### 1. Backend - Modelo de Datos

#### `apps/backend/app/models/core/products.py`
```python
# Línea 38-39: Nuevos campos
suggested_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
use_suggested_price: Mapped[bool] = mapped_column(Boolean, default=False)
```

### 2. Backend - Lógica de Cálculo

#### `apps/backend/app/services/recipe_calculator.py`
- **Función**: `calculate_recipe_cost()` (línea 20)
- **Cambios**:
  - Nuevo parámetro: `update_product_price: bool = True`
  - Calcula: `suggested_price = unit_cost * 2`
  - Sincroniza automáticamente con producto si tiene receta
  - Si `use_suggested_price=True`, actualiza `product.price`
- **Return**: Ahora incluye `suggested_price` en respuesta

### 3. Backend - Schemas Pydantic

#### `apps/backend/app/modules/products/interface/http/tenant.py`

**ProductCreate** (línea 61):
```python
suggested_price: float | None = Field(default=None, ge=0)
use_suggested_price: bool = False
```

**ProductUpdate** (línea 81):
```python
suggested_price: float | None = Field(default=None, ge=0)
use_suggested_price: bool | None = None
```

**ProductOut** (línea 101):
```python
suggested_price: float | None = None
use_suggested_price: bool = False
```

**Función helper** `_to_product_out_row()` (línea 182):
```python
suggested_price=float(row.suggested_price) if row.suggested_price is not None else None,
use_suggested_price=bool(row.use_suggested_price) if row.use_suggested_price is not None else False,
```

### 4. Backend - Endpoints de Productos

#### `apps/backend/app/modules/products/interface/http/tenant.py`

**create_product()** (línea 684):
```python
obj = Product(
    # ... campos existentes ...
    suggested_price=payload.suggested_price,
    use_suggested_price=payload.use_suggested_price,
    # ...
)
```

**update_product()** (línea 727):
```python
if payload.suggested_price is not None:
    obj.suggested_price = payload.suggested_price
if payload.use_suggested_price is not None:
    obj.use_suggested_price = payload.use_suggested_price
    # Si se habilita usar precio sugerido y hay precio sugerido
    if payload.use_suggested_price and obj.suggested_price:
        obj.price = obj.suggested_price
```

### 5. Backend - Endpoint de Sincronización

#### `apps/backend/app/modules/production/interface/http/tenant.py`

**Nuevo endpoint** (línea 1074):
```
POST /recipes/{recipe_id}/sync-product-price
```

Sincroniza manualmente el precio sugerido del producto:
```python
def sync_recipe_product_price(recipe_id: UUID, ...):
    result = calculate_recipe_cost(db, recipe_id, update_product_price=True)
    return {
        "success": True,
        "recipe_id": str(recipe_id),
        "suggested_price": result["suggested_price"],
        "unit_cost": result["unit_cost"],
        "message": "Precio sugerido sincronizado con el producto"
    }
```

### 6. Frontend - UI de Productos

#### `apps/tenant/src/modules/products/Form.tsx`

**Nueva sección** (línea 436-476):
```jsx
// Precio Sugerido desde Receta
<h2>Precio Sugerido desde Receta</h2>
<p>Si el producto tiene una receta, el precio sugerido se calcula automáticamente...</p>

// Campo readonly del precio sugerido
<input
  type="number"
  value={suggestedPrice}
  disabled
  className="bg-gray-100"
/>

// Checkbox para usar precio sugerido
{suggestedPrice > 0 && (
  <label>
    <input
      type="checkbox"
      checked={useSuggestedPrice}
      onChange={(e) => {
        setForm({ ...form, use_suggested_price: e.target.checked })
        if (e.target.checked) {
          setForm((prev) => ({ ...prev, price: suggestedPrice }))
        }
      }}
    />
    Usar Precio Sugerido
  </label>
)}
```

---

## Base de Datos - Migración

**Ubicación**: `ops/migrations/2026-02-21_000_add_suggested_price_to_products/`

### up.sql
```sql
ALTER TABLE products
    ADD COLUMN IF NOT EXISTS suggested_price NUMERIC(12, 2) NULL,
    ADD COLUMN IF NOT EXISTS use_suggested_price BOOLEAN DEFAULT FALSE;

UPDATE products SET use_suggested_price = FALSE WHERE use_suggested_price IS NULL;

COMMENT ON COLUMN products.suggested_price IS 'Auto-calculated price suggestion based on recipe cost';
COMMENT ON COLUMN products.use_suggested_price IS 'Flag to apply suggested_price as the selling price';
```

### down.sql
```sql
ALTER TABLE products
    DROP COLUMN IF EXISTS suggested_price,
    DROP COLUMN IF EXISTS use_suggested_price;
```

---

## Flujo de Uso

### 1. Crear Receta
```
Usuario → Producción → Recetas → Nueva Receta
↓
Seleccionar Producto
↓
Agregar Ingredientes (con costos)
↓
Sistema calcula:
  - total_cost
  - unit_cost = total_cost / yield_qty
  - suggested_price = unit_cost * 2
↓
Almacena suggested_price en Producto
```

### 2. Ver en Producto
```
Usuario → Productos → Editar Producto
↓
Sección "Precio Sugerido desde Receta"
↓
Muestra:
  - Precio Sugerido: $X.XX (readonly)
  - ☐ Usar Precio Sugerido (checkbox)
```

### 3. Aplicar Precio
```
Opción A (UI):
  ☐ Usar Precio Sugerido → checkbox marca
  ↓
  Precio se actualiza automáticamente
  ↓
  Guardar → price = suggested_price

Opción B (API):
  POST /recipes/{id}/sync-product-price
  ↓
  Devuelve suggested_price actualizado
```

---

## Ejemplo Práctico

### PAN TAPADO

| Concepto | Valor |
|----------|-------|
| Ingredientes | Harina, Agua, Sal, Levadura |
| Costo Total | $14.18 |
| Rendimiento | 216 unidades |
| **Costo/Unidad** | **$0.066** |
| **Precio Sugerido** | **$0.13** |
| Markup | 100% |
| Margen | 50% |

### En Pantalla
```
PRODUCTOS > Editar "PAN TAPADO"

Nombre: PAN TAPADO
Precio: 0.13 $

──────────────────────────────────
Precio Sugerido desde Receta

Precio Sugerido: 0.13 $ ✓ [readonly]
  Calculado automáticamente desde receta

☐ Usar Precio Sugerido
  ↓ Si marca: Aplicar precio sugerido como precio de venta

──────────────────────────────────
```

---

## API Endpoints

### GET /products/{id}
```json
{
  "id": "uuid",
  "name": "PAN TAPADO",
  "price": 0.13,
  "stock": 216,
  "suggested_price": 0.13,
  "use_suggested_price": true
}
```

### PUT /products/{id}
```json
{
  "use_suggested_price": true,
  "price": 0.13
}
```

### POST /recipes/{id}/sync-product-price
```json
{
  "success": true,
  "recipe_id": "uuid",
  "suggested_price": 0.13,
  "unit_cost": 0.066,
  "message": "Precio sugerido sincronizado con el producto"
}
```

---

## Características

✅ **Automático**: Se calcula al crear/modificar receta
✅ **No Forzado**: Usuario decide aplicar o mantener precio propio
✅ **Flexible**: Puede cambiar entre precio sugerido y manual
✅ **Sincronizable**: API endpoint para sincronizar manualmente
✅ **Configurable**: Markup ajustable en `recipe_calculator.py` línea 94
✅ **Auditable**: Campos comentados en base de datos

---

## Testing

### Test básico
```python
# 1. Crear producto
product = POST /products { "name": "TEST", "price": 0.0 }

# 2. Crear receta
recipe = POST /recipes {
  "product_id": product.id,
  "ingredients": [...]
}

# 3. Verificar precio sugerido
product_updated = GET /products/{product.id}
assert product_updated.suggested_price > 0

# 4. Aplicar precio
PUT /products/{product.id} {
  "use_suggested_price": true
}
assert product_updated.price == product_updated.suggested_price
```

### Script de test
```bash
python test_suggested_price.py
```

---

## Documentación Asociada

- `SUGGESTED_PRICE_FEATURE.md` - Documentación técnica completa
- `SUGGESTED_PRICE_QUICK_START.md` - Guía de usuario
- `test_suggested_price.py` - Script de testing

---

## Próximos Pasos Opcionales

1. **Margen Configurable**: Permitir que el usuario ajuste el markup (actualmente fijo en 100%)
2. **Histórico de Precios**: Guardar versiones anteriores de precio sugerido
3. **Análisis de Rentabilidad**: Dashboard mostrando margen real vs sugerido
4. **Sincronización Automática**: Opción para actualizar precio automáticamente al cambiar receta
5. **Alertas**: Notificar cuando hay diferencia entre precio sugerido y precio actual

---

## Consideraciones de Producción

1. **Migración**: Ejecutar `ops/migrations/2026-02-21_000_add_suggested_price_to_products/`
2. **Backward Compatibility**: Los campos son nullable, sin breaking changes
3. **Performance**: Sin impacto en queries existentes (nuevas columnas indexadas opcionalmente)
4. **Data**: Los productos existentes tendrán `suggested_price = NULL` y `use_suggested_price = FALSE`
5. **Rollback**: Down.sql disponible si es necesario revertir

---

**Implementación completada**: ✅
**Migración pendiente**: Ejecutar `ops/migrations/2026-02-21_000_add_suggested_price_to_products/`
**Documentación**: Completa
**Testing**: Script disponible en `test_suggested_price.py`
