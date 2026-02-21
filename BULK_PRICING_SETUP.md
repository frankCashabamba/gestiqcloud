# Configuración de Venta por Cantidad (Bulk Pricing)

## Overview

La característica de "Venta por Cantidad" permite configurar precios fijos para cantidades específicas de **cada producto**. Es especialmente útil para panaderías y negocios similares donde se vende por lotes (ej: 6 tapapados por $1, 12 roscas por $2).

## Estructura de Datos

### Frontend (Avanzado.tsx)

```typescript
type BulkPricingItem = {
    product_id: string   // ID del producto
    product_name?: string // Nombre del producto (opcional)
    quantity: number     // Cantidad de unidades (ej: 6)
    unit_price: number   // Precio total por conjunto (ej: 1.00)
}
```

### Backend (pos_config)

La configuración se almacena en `company_settings.pos_config` como JSON (array de items):

```json
{
    "bulk_pricing_items": [
        {
            "product_id": "prod-001",
            "quantity": 6,
            "unit_price": 1.00
        },
        {
            "product_id": "prod-002",
            "quantity": 12,
            "unit_price": 1.80
        }
    ]
}
```

## Ubicación en la UI

- **Ruta**: http://localhost:8082/kusi-panaderia/settings/operativo
- **Sección**: "Venta por Cantidad (Panadería)"
- **Interfaz**:
  - Dropdown para seleccionar producto
  - Campo de cantidad (unidades)
  - Campo de precio (por conjunto)
  - Botón "Agregar" para agregar a la lista
  - Tabla con todos los productos configurados
  - Botón "Eliminar" para cada producto

## Cálculo de Precio Unitario

El precio por unidad se calcula automáticamente:
```
precio_unitario = unit_price / quantity
Ejemplo: $1.00 / 6 = $0.1667 por unidad
```

## Cómo Usar

### 1. Agregar producto con bulk pricing

1. Ir a Configuración → Operativo
2. Desplazarse a la sección "Venta por Cantidad (Panadería)"
3. En el formulario "Agregar producto":
   - Seleccionar Producto: "Tapapados" (del dropdown)
   - Cantidad: 6
   - Precio: 1.00
4. Hacer clic en "Agregar"
5. El producto aparece en la tabla
6. Repetir para más productos
7. Hacer clic en "Save configuration" al final

### 2. Editar configuración de un producto

1. Hacer clic en el botón "Eliminar" del producto en la tabla
2. El producto se elimina de la lista
3. Ingresarlo nuevamente con los nuevos valores
4. Guardar configuración

### 3. Eliminar todos los productos

Simplemente elimina cada uno haciendo clic en "Eliminar"

### 4. Usar en la aplicación POS

La configuración se almacena en `pos_config` y puede ser accedida desde:

```python
# Backend
from app.services.bulk_pricing_service import BulkPricingService

pos_config = company_settings.pos_config
bulk_pricing_items = pos_config.get('bulk_pricing_items', []) if pos_config else []

# Obtener config para un producto específico
product_id = "prod-001"
bulk_config = BulkPricingService.get_bulk_config_for_product(product_id, bulk_pricing_items)

if bulk_config:
    quantity = bulk_config['quantity']
    unit_price = bulk_config['unit_price']
    price_per_unit = unit_price / quantity
```

## Validaciones

- **Producto**: Debe seleccionar uno del dropdown
- **Cantidad**: Mínimo 1 unidad
- **Precio**: Mínimo 0.00
- **Duplicados**: No se puede agregar el mismo producto dos veces
- Solo se guarda si todos los valores están configurados

## Para Limpiar la Configuración

Hacer clic en "Eliminar" para cada producto. Al guardar, se eliminará la configuración.

## Persistencia

- La configuración se persiste en la base de datos bajo `company_settings.pos_config`
- Es única por inquilino (tenant)
- No requiere migraciones adicionales (usa JSON existente)

## Ejemplo de Implementación en POS

```python
from app.modules.settings.interface.http.company import get_company_settings
from app.services.bulk_pricing_service import BulkPricingService

async def apply_bulk_pricing(product_id: str, quantity: int, tenant_id: UUID, unit_price: float):
    settings = await get_company_settings(tenant_id)
    pos_config = settings.get('pos_config', {})
    bulk_pricing_items = pos_config.get('bulk_pricing_items', [])
    
    # Buscar configuración para este producto
    bulk_config = BulkPricingService.get_bulk_config_for_product(product_id, bulk_pricing_items)
    
    if not bulk_config:
        return None  # No bulk pricing configured for this product
    
    # Calcular precio con bulk pricing
    result = BulkPricingService.calculate_bulk_price(
        quantity=quantity,
        bulk_config=bulk_config,
        unit_price=unit_price
    )
    
    return result
    # Returns:
    # {
    #     'uses_bulk_pricing': True,
    #     'quantity': 20,
    #     'calculation': {
    #         'num_complete_sets': 3,
    #         'remaining_units': 2,
    #         'price_per_unit': 0.1667
    #     },
    #     'total_from_sets': 3.00,
    #     'total_from_remaining': 0.33,
    #     'total_price': 3.33
    # }
```

## API Endpoints

### Obtener configuración actual

```bash
GET /api/v1/tenant/company-settings
```

Respuesta:
```json
{
    "pos_config": {
        "bulk_pricing": {
            "quantity": 6,
            "unit_price": 1.00
        },
        "receipt": { ... },
        "tax": { ... }
    }
}
```

### Actualizar configuración

```bash
PUT /api/v1/tenant/company-settings
```

Payload:
```json
{
    "pos_config": {
        "bulk_pricing": {
            "quantity": 5,
            "unit_price": 1.00
        },
        "receipt": { ... },
        "tax": { ... }
    }
}
```

## Notas

- La configuración es global por empresa/tenant
- Se recomienda validar en el POS que la cantidad sea un múltiplo de la cantidad configurada
- El precio se muestra en tiempo real en la interfaz de configuración
- Cambios toman efecto inmediatamente después de guardar
