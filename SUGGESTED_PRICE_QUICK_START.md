# Quick Start: Precio Sugerido desde Receta

## TL;DR

Sistema automático que calcula un **precio de venta sugerido** basado en el costo de ingredientes de una receta.

- **Fórmula**: Precio Sugerido = Costo Unitario × 2 (Markup 100%, Margen 50%)
- **Uso**: Checkbox en el formulario de productos para aplicar precio sugerido

## Pasos para Usar

### 1. Crear un Producto
```
Ir a: Productos → Nuevo Producto
Llenar datos básicos
Guardar
```

### 2. Crear una Receta para el Producto
```
Ir a: Producción → Recetas → Nueva Receta
Seleccionar el producto
Agregar ingredientes con costos
El sistema calcula automáticamente:
  - Costo total
  - Costo por unidad
  - Precio sugerido (costo × 2)
Guardar
```

### 3. Ver Precio Sugerido en Producto
```
Editar producto
Sección "Precio Sugerido desde Receta"
Verá:
  ✓ Precio Sugerido: $X.XX (calculado)
  ☐ Usar Precio Sugerido (checkbox)
```

### 4. Aplicar Precio Sugerido (Opción A)
```
Marcar: ☐ Usar Precio Sugerido
El campo "Precio" se actualiza automáticamente
Guardar
```

### 5. Aplicar Precio Sugerido (Opción B - API)
```bash
curl -X POST http://localhost:8000/api/v1/tenant/recipes/{recipe_id}/sync-product-price \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

Respuesta:
```json
{
  "success": true,
  "suggested_price": 0.13,
  "unit_cost": 0.066,
  "message": "Precio sugerido sincronizado con el producto"
}
```

## Ejemplo: PAN TAPADO

| Campo | Valor |
|-------|-------|
| Producto | PAN TAPADO |
| Ingredientes | Harina, Agua, Sal, Levadura |
| Costo Total | $14.18 |
| Rendimiento | 216 unidades |
| **Costo por Unidad** | **$0.066** |
| **Precio Sugerido** | **$0.13** |
| Markup | 100% |
| Margen | 50% |

En el formulario del producto:
```
Precio Sugerido: 0.13 $ ✓

☐ Usar Precio Sugerido
  → Al marcar, Precio = 0.13
```

## Características

✅ **Automático**: Se calcula cuando creas/modificas receta
✅ **Flexible**: Puedes mantener precio diferente al sugerido
✅ **Sincronizable**: Puedes actualizar manualmente desde API
✅ **Sin Forzado**: El usuario decide si aplicar o no
✅ **Markup Configurable**: Ajustable en `recipe_calculator.py` línea 94

## Campos Nuevos

### En Product Model
```python
suggested_price: float | None  # Precio calculado desde receta
use_suggested_price: bool      # Flag para usar como precio de venta
```

### En API Responses
```json
{
  "id": "uuid",
  "name": "Producto",
  "price": 0.13,
  "suggested_price": 0.13,
  "use_suggested_price": true
}
```

## Endpoints Disponibles

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/recipes/{id}/sync-product-price` | Sincronizar precio sugerido |
| GET | `/recipes/{id}/cost-breakdown` | Ver desglose de costos |
| PUT | `/products/{id}` | Actualizar producto (incluye use_suggested_price) |

## Flujo Completo

```
CREATE PRODUCT → CREATE RECIPE WITH INGREDIENTS →
CALCULATE COSTS → SET SUGGESTED_PRICE →
APPLY TO PRODUCT (checkbox) →
PRODUCT USES NEW PRICE
```

## Notas

- El precio sugerido se recalcula cada vez que modificas una receta
- Si no marques "Usar Precio Sugerido", el precio no cambia
- Puedes tener un precio diferente al sugerido si lo necesitas
- El markup de 100% (margen 50%) es estándar pero configurable

## Troubleshooting

**P: No veo el precio sugerido**
R: El producto debe tener una receta asociada con ingredientes

**P: El checkbox está deshabilitado**
R: Solo aparece cuando hay un precio sugerido disponible

**P: ¿Se actualiza automáticamente el precio?**
R: No, solo si marcas "Usar Precio Sugerido" o sincronizas vía API

**P: ¿Puedo cambiar el markup (100%)?**
R: Sí, edita `apps/backend/app/services/recipe_calculator.py` línea 94
Cambia: `suggested_price = round(unit_cost * 2, 2)`

## Archivos Clave

- UI: `apps/tenant/src/modules/products/Form.tsx` (línea 436+)
- Backend: `apps/backend/app/services/recipe_calculator.py` (línea 20+)
- API: `apps/backend/app/modules/products/interface/http/tenant.py`
- Modelo: `apps/backend/app/models/core/products.py` (línea 38+)

---

**Versión**: 1.0
**Última actualización**: 2026-02-21
