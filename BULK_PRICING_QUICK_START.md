# Guía Rápida: Venta por Cantidad (Bulk Pricing)

## Inicio Rápido (2 minutos)

### Paso 1: Ir a Configuración
1. Login en tu aplicación
2. Ir a **Configuración** → **Operativo**

### Paso 2: Agregar producto
Encontrarás la sección "**Venta por Cantidad (Panadería)**"

1. **Seleccionar Producto**: "Tapapados" (del dropdown)
2. **Cantidad**: `6`
3. **Precio**: `1.00`
4. Hacer clic en **Agregar**

### Paso 3: Agregar más productos
Repite el Paso 2 para cada producto:
- Roscas: 12 unidades × $1.80
- Biscochos: 24 unidades × $2.40
- Etc.

### Paso 4: Guardar
Hacer clic en **Save configuration** al final

## ¿Qué acaba de pasar?

✅ Se configuró "6 tapapados por $1.00"  
✅ Se configuró "12 roscas por $1.80"  
✅ Se configuró "24 biscochos por $2.40"

Ahora en el POS, cuando un cliente compre:
- 6 tapapados → pagará $1.00 ($0.1667 c/u)
- 18 tapapados → pagará $3.00 (3 sets de 6)
- 20 tapapados → pagará $3.33 (3 sets + 2 sueltas)

## Cambiar configuración

### Cambiar cantidad o precio de un producto

1. Hacer clic en **Eliminar** del producto en la tabla
2. Re-agregarlo con los nuevos valores
3. Guardar

### Eliminar un producto

1. Hacer clic en **Eliminar**
2. Guardar

## Ejemplos

### Scenario 1: Panadería básica
```
Tapapados:     6 unidades  × $1.00  = $0.1667 c/u
Roscas:       12 unidades  × $1.80  = $0.1500 c/u
Biscochos:    24 unidades  × $2.40  = $0.1000 c/u
```

### Scenario 2: Cliente compra
Cliente compra:
- 18 Tapapados
- 5 Roscas
- 50 Biscochos

Sistema calcula:
```
Tapapados:   3 sets × $1.00 = $3.00
Roscas:      0 sets + 5 sueltas × $0.15 = $0.75
Biscochos:   2 sets × $2.40 + 2 sueltas × $0.10 = $4.90
Total:       $3.00 + $0.75 + $4.90 = $8.65
```

## Validaciones

La aplicación te muestra error si:
- No seleccionas un producto
- Dejas la cantidad en 0
- Intentas agregar el mismo producto dos veces

## API (Para Developers)

### Obtener configuración

```bash
GET /api/v1/tenant/company-settings
```

Respuesta:
```json
{
    "pos_config": {
        "bulk_pricing_items": [
            {"product_id": "1", "quantity": 6, "unit_price": 1.00},
            {"product_id": "2", "quantity": 12, "unit_price": 1.80}
        ]
    }
}
```

### Usar en código

```python
from app.services.bulk_pricing_service import BulkPricingService

# Buscar config para un producto
bulk_items = pos_config.get('bulk_pricing_items', [])
bulk_config = BulkPricingService.get_bulk_config_for_product(
    product_id='1',
    bulk_pricing_items=bulk_items
)

# Calcular precio
if bulk_config:
    result = BulkPricingService.calculate_bulk_price(
        quantity=20,
        bulk_config=bulk_config
    )
    print(f"Total: ${result['total_price']}")
```

## Preguntas Frecuentes

**P: ¿Puedo cambiar de 6 a 5 unidades?**  
R: Sí, elimina y re-agrega el producto con la nueva cantidad.

**P: ¿Qué pasa si no configuro bulk pricing?**  
R: El sistema usa los precios unitarios normales de los productos.

**P: ¿Puedo tener el mismo producto dos veces?**  
R: No, la aplicación lo previene. Debes eliminar y re-agregar si quieres cambiar.

**P: ¿Se guarda automáticamente?**  
R: No, debes hacer clic en "Save configuration" al final.

**P: ¿Dónde se almacena?**  
R: En la base de datos, en el campo `company_settings.pos_config` como JSON.

## Archivos Técnicos

- **Frontend**: `apps/tenant/src/modules/settings/Avanzado.tsx`
- **Servicio Backend**: `apps/backend/app/services/bulk_pricing_service.py`
- **Tests**: `apps/backend/app/tests/test_bulk_pricing_service.py`
- **Documentación completa**: `BULK_PRICING_SETUP.md`
- **Integración**: `BULK_PRICING_INTEGRATION.md`
