# Módulo INVENTARIO - Documentación

## 📋 Descripción

Gestión de inventario con control de stock, movimientos, alertas y valoración. Integrado con el módulo de Productos.

Estado: Activo
Madurez: 4/5
Owner: Frontend
Riesgo: Alto

## Implementado

- Vista de stock con KPIs, filtros, alertas y exportación CSV.
- Registro de movimientos de inventario.
- Clientes API para almacenes, stock items, movimientos, ajustes, KPIs y valoración.

## Parcial

- La valoración depende de la implementación backend activa y del método seleccionado.
- La trazabilidad por lote/caducidad está expuesta en UI, pero requiere validación end-to-end con datos reales.

## Pendiente

- Vista de historial de movimientos completa.
- Pruebas de ajuste, transferencia, recepción y consumo desde POS/producción.
- Validación de stock negativo y concurrencia.

## Endpoints usados

- `GET /api/v1/tenant/inventory/warehouses`
- `POST /api/v1/tenant/inventory/warehouses`
- `PUT /api/v1/tenant/inventory/warehouses/:id`
- `GET /api/v1/tenant/inventory/stock-items`
- `GET /api/v1/tenant/inventory/stock-summary`
- `GET /api/v1/tenant/inventory/stock-moves`
- `POST /api/v1/tenant/inventory/stock-moves`
- `POST /api/v1/tenant/inventory/adjustments`

## Permisos

- `inventory:read`
- `inventory:create`
- `inventory:update`
- `inventory:manage-alerts`

## Tests mínimos

- Crear movimiento de entrada y verificar stock.
- Crear ajuste físico.
- Validar alertas de stock bajo/sobre-stock.
- Comprobar permisos en rutas y acciones.

## 🏗️ Arquitectura

```
apps/tenant/src/modules/inventario/
├── StockList.tsx         ✅ Vista de stock actual (KPIs + alertas + filtros)
├── MovimientoForm.tsx    ✅ Formulario nuevo movimiento (6 tipos)
├── Routes.tsx            ✅ Rutas configuradas
├── services.ts           ✅ API client (Warehouses + Stock + Moves)
├── manifest.ts           ✅ Configuración del módulo
└── README.md             📄 Este archivo
```

## ✨ Características

### **StockList.tsx** - Control de Stock
- ✅ **KPIs en tiempo real**:
  - Total productos en stock
  - Valor total del inventario (qty × precio)
  - Alertas de stock bajo
  - Productos con sobre-stock
- ✅ Filtros avanzados:
  - Búsqueda por nombre/código
  - Filtro por almacén
  - Filtro por alertas (bajo/sobre/todas)
- ✅ Ordenamiento por: almacén, producto, cantidad
- ✅ Paginación configurable (25/50/100)
- ✅ Exportación a CSV
- ✅ Alertas visuales:
  - 🔴 Stock bajo (qty < stock_minimo)
  - 🟠 Sobre-stock (qty > stock_maximo)
  - 🟢 OK (entre mínimo y máximo)
- ✅ Datos expandidos: producto, almacén, ubicación, lote, caducidad

### **MovimientoForm.tsx** - Registro de Movimientos
- ✅ **6 tipos de movimientos**:
  - 📦 Entrada por compra
  - 🏭 Entrada por producción
  - ↩️ Devolución de cliente
  - 📤 Salida por venta
  - ❌ Merma/Pérdida
  - ⚙️ Ajuste manual
- ✅ Selección de producto (solo activos)
- ✅ Selección de almacén (solo activos)
- ✅ Cantidad (auto-ajusta signo según tipo)
- ✅ Lote opcional
- ✅ Fecha de caducidad opcional
- ✅ Notas adicionales

### **services.ts** - API Client
- ✅ **Warehouses** (Almacenes):
  - `listWarehouses()`
  - `createWarehouse(data)`
  - `updateWarehouse(id, data)`
- ✅ **Stock Items** (Existencias):
  - `listStockItems(params)` - Con filtros opcionales
  - `getStockSummary()` - Resumen consolidado
  - `getStockByProduct(productId)` - Por producto
- ✅ **Stock Moves** (Movimientos):
  - `listStockMoves(params)` - Historial con filtros
  - `createStockMove(data)` - Nuevo movimiento
- ✅ **Ajustes**:
  - `createAdjustment(data)` - Recuento físico batch
- ✅ **KPIs y Reportes**:
  - `getInventoryKPIs()` - Métricas del dashboard
  - `getStockValuation(method)` - Valoración (FIFO/average/last)
  - `exportStockCSV()` - Export de stock

## 📊 Integración con Productos

### Relación 1:N (Producto → Stock Items)

```typescript
// 1 PRODUCTO puede tener múltiples STOCK ITEMS (diferentes almacenes)
Producto {
  id: "uuid-123"
  codigo: "PAN001"
  nombre: "Pan integral 400g"
  precio: 2.50
  stock_minimo: 50  ← Parámetro de alerta
  stock_maximo: 200 ← Parámetro de alerta
}
    ↓ tiene stock en
[
  StockItem {
    product_id: "uuid-123"
    warehouse_id: 1 (Almacén Central)
    qty: 120            ← Cantidad REAL
    ubicacion: "A3"
    lote: "LOT-001"
  },
  StockItem {
    product_id: "uuid-123"
    warehouse_id: 2 (Tienda 1)
    qty: 30             ← Cantidad REAL
    ubicacion: "Mostrador"
  }
]
```

### Flujo Operativo

#### 1. Crear Producto (Módulo PRODUCTOS)
```typescript
await createProducto({
  codigo: "PAN001",
  nombre: "Pan integral 400g",
  precio: 2.50,
  stock_minimo: 50,
  stock_maximo: 200
})
// Producto creado pero SIN stock inicial
```

#### 2. Entrada Inicial (Módulo INVENTARIO)
```typescript
await createStockMove({
  product_id: "uuid-123",
  warehouse_id: 1,
  qty: 100,  // Positivo = entrada
  kind: 'purchase'
})
// Backend auto-crea stock_item con qty=100 o actualiza si existe
```

#### 3. Venta (Módulo POS/VENTAS)
```typescript
// POS automáticamente crea stock_move con qty negativo
await createStockMove({
  product_id: "uuid-123",
  warehouse_id: 1,
  qty: -3,  // Negativo = salida
  kind: 'sale',
  ref_doc_id: 'ticket-001'
})
// Backend actualiza stock_item: qty = 97
```

#### 4. Alerta de Stock Bajo
```typescript
// En StockList.tsx se calcula:
if (stock_item.qty < producto.stock_minimo) {
  // Muestra badge rojo: "⚠️ Stock bajo"
}
// Usuario recibe alerta visual de reposición
```

## 🔧 Backend - Endpoints

### Base URL: `/api/v1/tenant/inventory`

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/warehouses` | Lista almacenes |
| POST | `/warehouses` | Crea almacén |
| PUT | `/warehouses/:id` | Actualiza almacén |
| DELETE | `/warehouses/:id` | Elimina almacén |
| GET | `/stock` | Lista stock con filtros opcionales |
| POST | `/stock/adjust` | Crea ajuste/movimiento (auto-actualiza stock) |
| POST | `/stock/transfer` | Transferencia entre almacenes |
| GET | `/alerts/configs` | Configuraciones de alertas |
| POST | `/alerts/configs` | Crear configuración de alertas |
| GET | `/alerts/history` | Historial de alertas |

## 🧪 Testing

### TEST 1: Ver Stock Actual

```bash
# 1. Acceder al módulo
http://localhost:8082/kusi-panaderia/inventario

# 2. Verificar que se muestran KPIs:
# - Total productos
# - Valor total stock
# - Alertas stock bajo
# - Sobre-stock
```

### TEST 2: Crear Entrada de Compra

```bash
# 1. Click "➕ Nuevo movimiento"
# 2. Seleccionar:
#    Tipo: 📦 Entrada por compra
#    Producto: Pan integral 400g
#    Almacén: Almacén Central
#    Cantidad: 200
#    Lote: LOT-2025-001
# 3. Click "Registrar movimiento"

# Resultado esperado:
# - Toast verde: "Movimiento registrado"
# - Stock se actualiza: qty += 200
# - Aparece en la tabla con lote
```

### TEST 3: Crear Salida por Venta

```bash
# 1. Nuevo movimiento
# 2. Tipo: 📤 Salida por venta
# 3. Producto: Pan integral 400g
# 4. Cantidad: 50
# 5. Registrar

# Resultado:
# - Stock se resta: qty -= 50
```

### TEST 4: Alerta de Stock Bajo

```bash
# 1. Crear producto con stock_minimo = 50
# 2. Crear entrada de 40 unidades
# 3. Ver en StockList

# Resultado:
# - Badge rojo: "⚠️ Stock bajo"
# - KPI "Alertas stock bajo" = 1
```

### TEST 5: Filtrar por Almacén

```bash
# 1. Tener stock en 2 almacenes diferentes
# 2. Seleccionar filtro "Almacén Central"

# Resultado:
# - Solo muestra productos de ese almacén
```

### TEST 6: Exportar CSV

```bash
# 1. Click "📥 Exportar CSV"

# Resultado:
# - Descarga stock-YYYY-MM-DD.csv
# - Contiene: Almacén, Código, Producto, Stock, Ubicación, Lote, Caducidad
```

### TEST 7: Ordenamiento por Cantidad

```bash
# 1. Click header "Stock"
# 2. Verificar orden ascendente (menor a mayor)
# 3. Click de nuevo
# 4. Verificar orden descendente (mayor a menor)
```

### TEST 8: Integración con Productos

```bash
# 1. Crear producto en módulo Productos
curl -X POST http://localhost:8000/api/v1/tenant/products \
  -H "Content-Type: application/json" \
  -d '{"codigo":"TEST001","nombre":"Producto Test","precio":10,"stock_minimo":10,"activo":true}'

# 2. Crear movimiento de entrada
curl -X POST http://localhost:8000/api/v1/tenant/inventory/stock/adjust \
  -H "Content-Type: application/json" \
  -d '{"product_id":"uuid-test","warehouse_id":1,"qty":50,"kind":"purchase"}'

# 3. Ver en inventario
curl http://localhost:8000/api/v1/tenant/inventory/stock?product_id=uuid-test

# Resultado:
# Stock creado con qty=50
```

## 📈 Valoración de Inventario

El módulo soporta 3 métodos de valoración:

### 1. **FIFO** (First In, First Out)
```
Entrada 1: 100 uds @ 10€ = 1,000€
Entrada 2: 50 uds @ 12€ = 600€
Salida: 120 uds

Valoración:
- Primero salen 100 uds @ 10€ = 1,000€
- Luego salen 20 uds @ 12€ = 240€
- Total coste: 1,240€
- Quedan: 30 uds @ 12€
```

### 2. **Promedio Ponderado**
```
Total comprado: 150 uds por 1,600€
Precio promedio: 1,600€ / 150 = 10.67€/ud

Salida de 120 uds:
Coste: 120 × 10.67€ = 1,280€
```

### 3. **Último Precio** (Last Purchase)
```
Última compra: 12€
Salida de 120 uds:
Coste: 120 × 12€ = 1,440€
```

## 🔄 Tipos de Movimientos

| Tipo | Signo | Uso | Actualiza Stock | Ejemplo |
|------|-------|-----|-----------------|---------|
| **purchase** | + | Compras a proveedores | ✅ Sí | Recibir mercancía |
| **production** | + | Producción interna | ✅ Sí | Hornear 200 panes |
| **return** | + | Devolución de cliente | ✅ Sí | Cliente devuelve producto |
| **sale** | - | Venta al cliente | ✅ Sí | Venta en POS |
| **loss** | - | Mermas/Pérdidas | ✅ Sí | Pan caducado |
| **adjustment** | +/- | Ajuste manual | ✅ Sí | Recuento físico |
| **transfer** | +/- | Entre almacenes | ✅ Sí | Mover stock |

## ⚙️ Configuración de Almacenes

### Crear Almacén

```typescript
await createWarehouse({
  code: 'ALM-01',
  name: 'Almacén Central',
  is_active: true,
  metadata: {
    direccion: 'Calle Principal 123',
    capacidad_m3: 500
  }
})
```

### Almacenes por Sector

**PANADERÍA:**
- Almacén Central (materias primas)
- Tienda/Mostrador (productos terminados)

**RETAIL/BAZAR:**
- Almacén Principal
- Tienda 1, Tienda 2 (multi-tienda)
- Trastienda

**TALLER MECÁNICO:**
- Almacén de repuestos
- Mostrador
- Taller (work in progress)

## 🎯 KPIs del Dashboard

```typescript
{
  total_productos: 250,
  total_stock_value: 12450.50,  // Suma de (qty × precio)
  productos_bajo_stock: 15,      // qty < stock_minimo
  productos_sobre_stock: 3,      // qty > stock_maximo
  movimientos_hoy: 42,
  ultimo_ajuste: "2025-10-29T15:30:00"
}
```

## 🐛 Problemas Comunes

### "El stock no se actualiza después de crear movimiento"
**Solución:**
1. Verificar que `kind` es correcto
2. Verificar que `qty` tiene el signo apropiado
3. Refrescar lista (el backend auto-actualiza stock_items)

### "No aparece el producto en el selector"
**Solución:**
1. Verificar que el producto está `activo: true`
2. Verificar que el producto existe en módulo Productos
3. Recargar página (caché)

### "Alerta de stock bajo no aparece"
**Solución:**
1. Verificar que el producto tiene `stock_minimo` definido
2. Verificar que `qty < stock_minimo`
3. Refrescar filtros

## 🚀 Próximas Mejoras

### V1.1
- [ ] Vista de movimientos (historial detallado)
- [ ] Ajuste de inventario batch (importar CSV)
- [ ] Transferencias entre almacenes (UI)
- [ ] Dashboard avanzado con gráficos

### V1.2
- [ ] Valoración real con FIFO/Average
- [ ] Kardex por producto
- [ ] Reportes de rotación
- [ ] Integración con compras (auto-crear entrada)

---

**Versión:** 1.0.0
**Estado:** Activo (validar cobertura con tests en CI)
**Última revisión documental:** Febrero 2026
