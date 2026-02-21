# Integración de Bulk Pricing en el POS

## Resumen

Este documento explica cómo integrar la funcionalidad de "venta por cantidad" en los endpoints del POS.

## Servicio Backend

### Ubicación
`apps/backend/app/services/bulk_pricing_service.py`

### Funciones Principales

#### 1. `calculate_bulk_price()`

Calcula el precio basado en la configuración de bulk pricing.

```python
from app.services.bulk_pricing_service import BulkPricingService

# Obtener config
pos_config = company_settings.pos_config
bulk_config = pos_config.get('bulk_pricing') if pos_config else None

# Calcular precio
result = BulkPricingService.calculate_bulk_price(
    quantity=18,
    bulk_config=bulk_config,
    unit_price=0.5  # Fallback si no hay bulk pricing
)

print(result)
# Output:
# {
#     'uses_bulk_pricing': True,
#     'calculation': {
#         'num_complete_sets': 3,
#         'remaining_units': 0,
#         'price_per_unit': 0.1667
#     },
#     'total_price': 3.00
# }
```

#### 2. `validate_bulk_config()`

Valida que la configuración sea correcta.

```python
is_valid, error_msg = BulkPricingService.validate_bulk_config(bulk_config)

if not is_valid:
    print(f"Error de configuración: {error_msg}")
```

#### 3. `format_bulk_pricing_display()`

Formatea la configuración para mostrar en UI.

```python
display = BulkPricingService.format_bulk_pricing_display(bulk_config)
# Output: "6 units for $1.00"
```

## Ejemplo de Integración en Endpoint POS

### Crear Venta con Bulk Pricing

```python
from fastapi import APIRouter, Depends
from app.services.bulk_pricing_service import BulkPricingService
from app.modules.settings.interface.http.company import get_company_settings

router = APIRouter(prefix="/api/v1/tenant/pos", tags=["POS"])

@router.post("/sales")
async def create_sale(
    tenant_id: UUID,
    sale_data: SaleCreateSchema,
):
    """Create a sale with bulk pricing calculation."""
    
    # Obtener configuración de la empresa
    company_settings = await get_company_settings(tenant_id)
    pos_config = company_settings.get('pos_config', {})
    bulk_config = pos_config.get('bulk_pricing')
    
    # Procesar cada item de la venta
    total_amount = 0
    
    for item in sale_data.items:
        # Calcular precio con bulk pricing si aplica
        pricing = BulkPricingService.calculate_bulk_price(
            quantity=item.quantity,
            bulk_config=bulk_config,
            unit_price=item.product.price
        )
        
        # Usar el precio calculado
        item_total = pricing['total_price']
        total_amount += item_total
        
        # Guardar información de pricing en el item
        sale_item.bulk_pricing_applied = pricing['uses_bulk_pricing']
        sale_item.unit_price_effective = pricing['unit_price_effective']
    
    # Crear la venta
    sale = Sale(
        tenant_id=tenant_id,
        total_amount=total_amount,
        items=sale_items
    )
    
    db.add(sale)
    db.commit()
    
    return {"status": "success", "sale_id": sale.id, "total": total_amount}
```

### Obtener Configuración de Bulk Pricing

```python
@router.get("/config/bulk-pricing")
async def get_bulk_pricing(tenant_id: UUID):
    """Get bulk pricing configuration for the store."""
    
    company_settings = await get_company_settings(tenant_id)
    pos_config = company_settings.get('pos_config', {})
    bulk_config = pos_config.get('bulk_pricing')
    
    if not bulk_config:
        return {
            "enabled": False,
            "config": None
        }
    
    is_valid, error = BulkPricingService.validate_bulk_config(bulk_config)
    
    if not is_valid:
        return {
            "enabled": False,
            "error": error
        }
    
    return {
        "enabled": True,
        "quantity": bulk_config['quantity'],
        "price": bulk_config['unit_price'],
        "display": BulkPricingService.format_bulk_pricing_display(bulk_config),
        "price_per_unit": bulk_config['unit_price'] / bulk_config['quantity']
    }
```

### Calcular Estimado de Venta

```python
@router.post("/sales/estimate")
async def estimate_sale(
    tenant_id: UUID,
    items: list[SaleItemEstimate]
):
    """Estimate total sale with bulk pricing."""
    
    company_settings = await get_company_settings(tenant_id)
    pos_config = company_settings.get('pos_config', {})
    bulk_config = pos_config.get('bulk_pricing')
    
    breakdown = []
    total = 0
    
    for item in items:
        pricing = BulkPricingService.calculate_bulk_price(
            quantity=item.quantity,
            bulk_config=bulk_config,
            unit_price=item.unit_price
        )
        
        breakdown.append({
            "product_id": item.product_id,
            "quantity": item.quantity,
            "pricing": pricing
        })
        
        total += pricing['total_price']
    
    return {
        "items": breakdown,
        "total": round(total, 2),
        "bulk_pricing_config": bulk_config
    }
```

## Casos de Uso

### Caso 1: Cliente compra exactamente 6 tapapados

```
Configuración: 6 unidades por $1.00
Cliente compra: 6 unidades
Resultado:
  - Sets completos: 1
  - Unidades restantes: 0
  - Precio total: $1.00
  - Precio por unidad: $0.1667
```

### Caso 2: Cliente compra 8 tapapados

```
Configuración: 6 unidades por $1.00
Cliente compra: 8 unidades
Resultado:
  - Sets completos: 1 × $1.00 = $1.00
  - Unidades restantes: 2 × $0.1667 = $0.33
  - Precio total: $1.33
```

### Caso 3: Cliente compra 3 tapapados

```
Configuración: 6 unidades por $1.00
Cliente compra: 3 unidades
Resultado:
  - Sets completos: 0
  - Unidades restantes: 3 × $0.1667 = $0.50
  - Precio total: $0.50
```

## Cambiar Configuración en el Futuro

Si necesitas cambiar de 6 a 5 unidades por $1:

1. Ve a Configuración → Operativo → "Venta por Cantidad (Panadería)"
2. Cambia "Cantidad" de 6 a 5
3. Mantén "Precio" en 1.00
4. Guarda la configuración

El sistema automáticamente:
- Actualizará el cálculo de precio por unidad a $0.20
- Aplicará el nuevo cálculo en todas las nuevas ventas
- Las ventas anteriores mantienen su precio histórico

## Testing

### Ejecutar tests

```bash
cd apps/backend
pytest app/tests/test_bulk_pricing_service.py -v
```

### Tests incluidos

- ✅ Cálculo con sets completos
- ✅ Cálculo con remainders
- ✅ Validación de configuración
- ✅ Formato para display
- ✅ Manejo de configuraciones inválidas
- ✅ Casos edge

## Notas Importantes

1. **Compatibilidad hacia atrás**: El campo `bulk_pricing` es opcional. Si no existe, el POS funciona normalmente con precios unitarios.

2. **Validación**: Siempre valida la configuración antes de usar.

3. **Precisión**: Los cálculos se redondean a 2 decimales para precios y 4 para precio unitario.

4. **Performance**: La configuración se obtiene una vez por operación, no por item.

5. **Seguridad**: La configuración es específica por tenant y se valida en cada endpoint.

## Migración Futura

Si en el futuro necesitas:
- Múltiples configuraciones por categoría
- Horarios diferentes para bulk pricing
- Excepciones por producto

Puedes extender `BulkPricingService` sin cambiar la estructura de datos existente.
