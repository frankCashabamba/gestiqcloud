# Guía de Implementación: Estandarización Inglés

## Estado: EN PROGRESO

Se han actualizado los siguientes archivos de modelos a inglés:

### ✅ Modelos Python Actualizados

1. **suppliers/proveedor.py** → `Supplier`, `SupplierContact`, `SupplierAddress`
   - Tabla: `proveedores` → `suppliers`
   - Tabla: `proveedor_contactos` → `supplier_contacts`
   - Tabla: `proveedor_direcciones` → `supplier_addresses`
   - Columnas: `codigo→code`, `nombre→name`, `nombre_comercial→trade_name`, `telefono→phone`, `web→website`, `activo→is_active`

2. **purchases/compra.py** → `Purchase`, `PurchaseLine`
   - Tabla: `compras` → `purchases`
   - Tabla: `compra_lineas` → `purchase_lines`
   - Columnas: `numero→number`, `proveedor_id→supplier_id`, `fecha→date`, `impuestos→taxes`, `estado→status`, etc.

3. **sales/venta.py** → `Sale`
   - Tabla: `ventas` → `sales`
   - Columnas: `numero→number`, `cliente_id→customer_id`, `fecha→date`, `impuestos→taxes`, `estado→status`, etc.

4. **expenses/gasto.py** → `Expense`
   - Tabla: `gastos` → `expenses`
   - Columnas: `fecha→date`, `concepto→concept`, `categoria→category`, `importe→amount`, `iva→vat`, `proveedor_id→supplier_id`, etc.

5. **finance/banco.py** → `BankMovement`
   - Tabla: `banco_movimientos` → `bank_movements`
   - Columnas: `cuenta_id→account_id`, `fecha→date`, `tipo→type`, `concepto→concept`, `importe→amount`, etc.

6. **hr/nomina.py** → `Nomina` (parcialmente)
   - Tabla: `nominas` → `payrolls`
   - Columnas: `numero→number`, `empleado_id→employee_id`, `periodo_mes→period_month`, `periodo_ano→period_year`, etc.

### 📋 Migraciones SQL Creadas

**Archivo:** `ops/migrations/2025-11-17_001_spanish_to_english_names/up.sql`
**Archivo:** `ops/migrations/2025-11-17_001_spanish_to_english_names/down.sql`

Las migraciones incluyen:
- Renombrado de 26+ tablas
- Actualización de 100+ columnas
- Recreación de Foreign Keys

### ⚠️ PENDIENTE: Actualizar Referencias

Se debe actualizar en toda la codebase:

#### 1. **Imports en servicios y routers**
```python
# Cambiar de:
from app.models.suppliers.proveedor import Proveedor, ProveedorContacto, ProveedorDireccion
from app.models.purchases.compra import Compra, CompraLinea
from app.models.sales.venta import Venta

# A:
from app.models.suppliers.proveedor import Supplier, SupplierContact, SupplierAddress
from app.models.purchases.compra import Purchase, PurchaseLine
from app.models.sales.venta import Sale
```

#### 2. **Servicios (services/)**
Buscar y reemplazar todas las referencias a nombres antiguos en:
- `services/suppliers/`
- `services/purchases/`
- `services/sales/`
- `services/expenses/`
- `services/finance/`
- `services/hr/`

#### 3. **Routers/Endpoints (routers/)**
Actualizar tipos de respuesta y parámetros en:
- `routers/suppliers.py`
- `routers/purchases.py`
- `routers/sales.py`
- `routers/expenses.py`
- `routers/finance.py`
- `routers/hr.py`

#### 4. **Esquemas Pydantic (schemas/)**
Actualizar nombres de campos en:
- `schemas/suppliers/`
- `schemas/purchases/`
- `schemas/sales/`
- `schemas/expenses/`
- `schemas/finance/`
- `schemas/hr/`

#### 5. **Tests**
Actualizar referencias en:
- `tests/modules/`

### 🔍 Búsquedas Necesarias

Ejecutar búsquedas en toda la codebase:

```bash
# Búsquedas por patrón:
grep -r "Proveedor" app/
grep -r "Compra" app/
grep -r "Venta" app/
grep -r "Gasto" app/
grep -r "BancoMovimiento" app/
grep -r "Nomina" app/
grep -r "empleado_id" app/
grep -r "proveedor_id" app/
```

### ✅ Checklist de Implementación

- [ ] Ejecutar migración SQL en dev
- [ ] Actualizar imports en servicios
- [ ] Actualizar referencias en routers
- [ ] Actualizar esquemas Pydantic
- [ ] Actualizar tests
- [ ] Verificar que la aplicación inicia sin errores
- [ ] Ejecutar tests completos
- [ ] Hacer backup y ejecutar migración en producción

### 📝 Notas

1. Los nombres de clase Python no cambian la funcionalidad, solo la claridad
2. La migración SQL es bidireccional (up.sql / down.sql)
3. Se recomienda ejecutar en dev primero y validar antes de producción
4. Las FK y relaciones se actualizan automáticamente con los cambios de tabla
