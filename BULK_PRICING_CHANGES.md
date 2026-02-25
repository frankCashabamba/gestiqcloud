# Cambios Implementados: Venta por Cantidad (Bulk Pricing)

## Resumen

Se ha agregado una nueva configuración en la sección "Operativo" que permite definir precios fijos para cantidades específicas de **cada producto**. Ideal para panaderías donde se vende "6 tapapados por $1", "12 roscas por $2", etc. Ahora puedes configurar múltiples productos con diferentes bulk pricing.

## Archivos Modificados

### Frontend
- **`apps/tenant/src/modules/settings/Avanzado.tsx`**
  - Agregado tipo `BulkPricing` con campos `quantity` y `unit_price`
  - Agregado campo `bulk_pricing` a `PosForm`
  - Cargado y guardado de configuración en `loadSettings()` y `save()`
  - Agregada nueva sección UI "Venta por Cantidad (Panadería)"
  - Cálculo automático y visualización de precio unitario

### Backend - Servicios
- **`apps/backend/app/services/bulk_pricing_service.py`** (NUEVO)
  - Servicio para calcular precios con bulk pricing
  - Métodos:
    - `calculate_bulk_price()`: Calcula precio total y breakdowns
    - `validate_bulk_config()`: Valida la configuración
    - `format_bulk_pricing_display()`: Formatea para UI

### Backend - Tests
- **`apps/backend/app/tests/test_bulk_pricing_service.py`** (NUEVO)
  - Tests unitarios completos para `BulkPricingService`
  - Cobertura de casos normal, edge, e inválidos
  - 18+ test cases

### Documentación
- **`BULK_PRICING_SETUP.md`** (NUEVO)
  - Guía de configuración y uso
  - Ejemplos de datos
  - API endpoints

- **`BULK_PRICING_INTEGRATION.md`** (NUEVO)
  - Guía de integración para developers
  - Ejemplos de código
  - Casos de uso

- **`BULK_PRICING_CHANGES.md`** (ESTE ARCHIVO)
  - Resumen de cambios

## Estructura de Datos

### En la Base de Datos

La configuración se almacena en `company_settings.pos_config` como JSON (array):

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
    ],
    "receipt": { ... },
    "tax": { ... },
    "store_credit": { ... }
}
```

### En el Frontend

```typescript
type BulkPricingItem = {
    product_id: string   // ID del producto
    product_name?: string // Nombre (opcional)
    quantity: number     // Ejemplo: 6
    unit_price: number   // Ejemplo: 1.00
}
```

## Ubicación en la UI

**Ruta**: `http://localhost:8082/kusi-panaderia/settings/operativo`

**Sección**: "Venta por Cantidad (Panadería)" (después de "Precios incluyen impuestos" y antes de "Numeración")

**Interfaz**:
1. **Formulario de agregar**:
   - Dropdown: Seleccionar Producto (carga desde API)
   - Input: Cantidad (unidades)
   - Input: Precio (por conjunto)
   - Botón: "Agregar" (valida y agrega a la tabla)

2. **Tabla de configurados**:
   - Columna: Producto (nombre)
   - Columna: Cantidad
   - Columna: Precio
   - Columna: Precio/Unidad (calculado automáticamente)
   - Columna: Acción "Eliminar"

**Validaciones**:
- Debe seleccionar un producto
- Cantidad mínimo 1
- No se puede agregar el mismo producto dos veces
- Muestra error si faltan campos

## Cómo Usar

### Agregar producto con bulk pricing

1. Ir a Configuración → Operativo
2. Desplazarse a "Venta por Cantidad (Panadería)"
3. En el formulario:
   - Seleccionar Producto: "Tapapados" (dropdown)
   - Cantidad: 6
   - Precio: 1.00
4. Hacer clic en "Agregar"
5. El producto aparece en la tabla
6. Repetir para más productos (Roscas, Biscochos, etc.)
7. Hacer clic en "Save configuration" al final

### Cambiar configuración de un producto

1. Hacer clic en "Eliminar" del producto
2. Re-agregarlo con los nuevos valores
3. Guardar

### Eliminar un producto

1. Hacer clic en "Eliminar" en la tabla
2. Guardar

## Integración en Endpoints

Para usar en un endpoint del POS:

```python
from app.services.bulk_pricing_service import BulkPricingService

# Obtener config
pos_config = company_settings.pos_config
bulk_pricing_items = pos_config.get('bulk_pricing_items', [])

# Obtener config para un producto específico
product_id = "prod-001"
bulk_config = BulkPricingService.get_bulk_config_for_product(product_id, bulk_pricing_items)

if bulk_config:
    # Calcular precio
    result = BulkPricingService.calculate_bulk_price(
        quantity=18,
        bulk_config=bulk_config,
        unit_price=0.5
    )

    print(result)
    # {
    #     'uses_bulk_pricing': True,
    #     'calculation': {
    #         'num_complete_sets': 3,
    #         'remaining_units': 0,
    #         'price_per_unit': 0.1667
    #     },
    #     'total_from_sets': 3.00,
    #     'total_from_remaining': 0.0,
    #     'total_price': 3.00
    # }
else:
    # Usar precio unitario normal
    total = quantity * unit_price
```

## Testing

### Ejecutar tests

```bash
cd apps/backend
pytest app/tests/test_bulk_pricing_service.py -v
```

### Casos cubiertos

- ✅ Cálculo con sets completos
- ✅ Cálculo con remainders (unidades sueltas)
- ✅ Cantidad menor al set size
- ✅ Validación de config
- ✅ Config inválidas o malformadas
- ✅ Edge cases

## Notas Importantes

1. **Sin cambios en migraciones**: La configuración usa el JSON existente en `pos_config`, no requiere cambios en la BD.

2. **Opcional**: Si `bulk_pricing` no está configurado, el sistema funciona normalmente con precios unitarios.

3. **Seguridad**: Es específica por tenant, no afecta a otras empresas.

4. **Precisión**:
   - Precios redondeados a 2 decimales
   - Precio por unidad con 4 decimales

5. **Retrocompatibilidad**: Cambios 100% compatibles con código existente.

## Ejemplos de Cálculo

### Configuración en la tabla:

| Producto | Cantidad | Precio | Precio/Unidad |
|----------|----------|--------|---------------|
| Tapapados | 6 | $1.00 | $0.1667 |
| Roscas | 12 | $1.80 | $0.1500 |
| Biscochos | 24 | $2.40 | $0.1000 |

### Ejemplo 1: Cliente compra 18 Tapapados
```
Config: 6 unidades por $1.00
Compra: 18 unidades
Resultado:
  - 3 sets × $1.00 = $3.00
  - 0 unidades sueltas = $0.00
  - Total = $3.00
```

### Ejemplo 2: Cliente compra 20 Tapapados
```
Config: 6 unidades por $1.00
Compra: 20 unidades
Resultado:
  - 3 sets × $1.00 = $3.00
  - 2 unidades × $0.1667 = $0.33
  - Total = $3.33
```

### Ejemplo 3: Cliente compra 3 Roscas
```
Config: 12 unidades por $1.80
Compra: 3 unidades
Resultado:
  - 0 sets × $1.80 = $0.00
  - 3 unidades × $0.1500 = $0.45
  - Total = $0.45
```

### Ejemplo 4: Cliente compra 30 Biscochos
```
Config: 24 unidades por $2.40
Compra: 30 unidades
Resultado:
  - 1 set × $2.40 = $2.40
  - 6 unidades × $0.1000 = $0.60
  - Total = $3.00
```

## Próximos Pasos (Opcional)

Si quieres implementar más características en el futuro:

1. **Usar en POS**: Integrar en endpoint de ventas
2. **Reportes**: Mostrar cuántas ventas usaron bulk pricing
3. **Por categoría**: Diferentes bulk pricing por tipo de producto
4. **Por horario**: Bulk pricing diferente en horas pico
5. **Excepciones**: Productos excluidos del bulk pricing

## Soporte

Para preguntas o problemas:
1. Revisar `BULK_PRICING_SETUP.md` para configuración
2. Revisar `BULK_PRICING_INTEGRATION.md` para integración
3. Ejecutar tests: `pytest app/tests/test_bulk_pricing_service.py -v`
