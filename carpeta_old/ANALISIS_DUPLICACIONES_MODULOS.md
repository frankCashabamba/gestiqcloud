# ANÁLISIS DE DUPLICACIONES - MÓDULOS CRÍTICOS

**Fecha:** 2025-11-05  
**Objetivo:** Identificar funcionalidades duplicadas entre backend (Python) y frontend (TypeScript) para eliminar lógica de negocio del cliente.

---

## 1. FACTURACIÓN

### Backend (Python)
**Ubicación:** `apps/backend/app/modules/facturacion/`

#### Archivos principales:
- `schemas.py` - Esquemas Pydantic con validación
- `services.py` - Lógica de negocio (generación de números, procesamiento)
- `crud.py` - Operaciones CRUD
- `interface/http/tenant.py` - Endpoints REST

#### Funcionalidades implementadas:
✅ **Generación automática de números de factura** (atómico con SQL)
```python
def generar_numero_factura(db: Session, tenant_id: str) -> str:
    # Usa función SQL assign_next_number() para evitar colisiones
    # Formato: "A-YYYY-NNNNNN"
```

✅ **Validación de modelos polimórficos por sector**
- `LineaPanaderia` (tipo_pan, gramos)
- `LineaTaller` (repuesto, horas_mano_obra)
- Discriminador por campo `sector`

✅ **Endpoints REST completos:**
- `GET /facturacion/` - Listar facturas
- `POST /facturacion/` - Crear con líneas
- `PUT /facturacion/{id}` - Actualizar (solo borradores)
- `DELETE /facturacion/{id}` - Anular (soft delete)
- `POST /facturacion/{id}/emitir` - Emitir factura
- `GET /facturacion/{id}/pdf` - Generar PDF con WeasyPrint

✅ **Validaciones de estado:**
- Solo borradores pueden editarse
- Facturas pagadas no pueden anularse
- Cálculo de totales en backend

### Frontend (TypeScript)
**Ubicación:** `apps/tenant/src/modules/facturacion/`

#### Archivos principales:
- `services.ts` - Cliente API
- `Form.tsx` - Formulario de creación
- `List.tsx` - Listado de facturas
- `components/FacturaStatusBadge.tsx` - UI de estados

#### Funcionalidades implementadas:
⚠️ **Tipos duplicados:**
```typescript
export interface Invoice {
  id: number
  numero?: string
  fecha: string
  subtotal?: number
  iva?: number
  total: number
  estado?: string
  cliente_id?: number
}
```

⚠️ **Funciones utilitarias locales:**
```typescript
export function formatInvoiceNumber(invoice: Invoice): string {
  return invoice.numero || `INV-${invoice.id}`
}

export function getInvoiceStatusColor(status: string): string {
  const colors = {
    'draft': 'gray',
    'sent': 'blue',
    'paid': 'green',
    'overdue': 'red',
    'cancelled': 'red'
  }
  return colors[status as keyof typeof colors] || 'gray'
}

export function getEinvoiceStatusColor(status: string): string {
  const colors = {
    'PENDING': 'yellow',
    'SENT': 'blue',
    'AUTHORIZED': 'green',
    'REJECTED': 'red',
    'ERROR': 'red'
  }
  return colors[status as keyof typeof colors] || 'gray'
}
```

❌ **NO hay cálculos de negocio en frontend** - ✅ BIEN

### Duplicaciones Detectadas

| Elemento | Backend | Frontend | Acción |
|----------|---------|----------|--------|
| **Mapeo de estados a colores** | ❌ No existe | ✅ Existe | Mantener en frontend (UI) |
| **Formato de número de factura** | ✅ Lógica atómica | ⚠️ Fallback UI | ✅ OK (display only) |
| **Validación de estados** | ✅ Completa | ❌ No existe | ✅ OK |
| **Generación de números** | ✅ SQL atómico | ❌ No existe | ✅ OK |

### Recomendación
✅ **Mantener:** Backend tiene toda la lógica de negocio  
✅ **Frontend correcto:** Solo UI y llamadas API  
⚠️ **Considerar migrar:** Los enums de estados y colores podrían venir desde un endpoint `/api/v1/config/invoice_statuses` para centralizar

---

## 2. INVENTARIO

### Backend (Python)
**Ubicación:** `apps/backend/app/modules/inventario/`

#### Archivos principales:
- `interface/http/tenant.py` - Endpoints REST

#### Funcionalidades implementadas:
✅ **CRUD de almacenes (Warehouses):**
- `GET/POST/PUT/DELETE /inventory/warehouses`
- Soporte de metadata personalizada

✅ **Gestión de stock:**
- `GET /inventory/stock` - Consulta con joins (producto + almacén)
- `POST /inventory/stock/adjust` - Ajuste atómico con moves
- `POST /inventory/stock/transfer` - Transferencias entre almacenes
- `POST /inventory/stock/cycle_count` - Conteo cíclico

✅ **Validaciones críticas:**
```python
# Validación de stock insuficiente
if (src_item.qty or 0) < payload.qty:
    raise HTTPException(status_code=400, detail="insufficient_stock")

# Actualización atómica de stock agregado en productos
total_qty = db.query(func.sum(StockItem.qty)).filter(...).scalar()
prod.stock = float(total_qty)
```

✅ **Movimientos de stock:**
- Registro de todos los cambios en `stock_moves`
- Tipos: receipt, issue, adjustment, transfer, production, return, loss
- Referencia a documentos origen

### Frontend (TypeScript)
**Ubicación:** `apps/tenant/src/modules/inventario/`

#### Archivos principales:
- `services.ts` - Cliente API
- `StockList.tsx` - Listado de stock
- `MovimientoForm.tsx` - Formulario de movimientos
- `components/AlertasConfig.tsx` - Configuración de alertas

#### Funcionalidades implementadas:
⚠️ **Tipos duplicados (necesarios para TypeScript):**
```typescript
export type StockItem = {
  id: string
  product_id: string
  warehouse_id: string
  qty: number
  location?: string | null
  lot?: string | null
  product?: {
    sku: string
    name: string
    price: number
    product_metadata?: {
      reorder_point?: number
      max_stock?: number
    }
  }
}

export type StockMove = {
  id: string
  product_id: string
  warehouse_id: string
  qty: number
  kind: 'purchase' | 'sale' | 'adjustment' | 'transfer' | 'production' | 'return' | 'loss'
  ref_doc_type?: string | null
  ref_doc_id?: string | null
  notes?: string | null
}
```

❌ **NO hay cálculos de stock en frontend** - ✅ BIEN  
❌ **NO hay validaciones de negocio** - ✅ BIEN  

⚠️ **Normalización de datos del backend:**
```typescript
// Normalizar nombres de campos ES -> EN
const normProduct = {
  sku: p.sku ?? p.codigo ?? '',
  name: p.name ?? p.nombre ?? '',
  price: Number(p.price ?? p.precio ?? 0) || 0,
}
```

### Duplicaciones Detectadas

| Elemento | Backend | Frontend | Acción |
|----------|---------|----------|--------|
| **Validación stock insuficiente** | ✅ Completa | ❌ No existe | ✅ OK |
| **Cálculo de stock total** | ✅ SQL agregado | ❌ No existe | ✅ OK |
| **Enums de tipos de movimiento** | ✅ Implícito | ⚠️ Hardcoded en types | 🔄 Migrar a constantes compartidas |
| **Normalización ES/EN** | ❌ No existe | ⚠️ En frontend | 🔄 Backend debería devolver schema consistente |

### Recomendación
✅ **Mantener:** Backend tiene toda la lógica crítica  
⚠️ **Migrar a backend:** Normalización de nombres de campos (decidir un idioma único)  
🗑️ **Eliminar del frontend:** Ninguna lógica crítica detectada  
⚠️ **Estandarizar:** Los enums de `StockMove.kind` deberían venir de un schema compartido

---

## 3. VENTAS

### Backend (Python)
**Ubicación:** `apps/backend/app/modules/ventas/`

#### Archivos principales:
- `interface/http/tenant.py` - Endpoints REST
- `infrastructure/repositories.py` - Repositorios

#### Funcionalidades implementadas:
✅ **CRUD de órdenes de venta:**
- `GET /sales_orders/` - Listar órdenes
- `POST /sales_orders/` - Crear orden con items
- `GET /sales_orders/{id}` - Obtener orden
- `POST /sales_orders/{id}/confirm` - Confirmar orden

✅ **Validaciones de estado:**
```python
if so.status != "draft":
    raise HTTPException(status_code=400, detail="invalid_status")
if not items:
    raise HTTPException(status_code=400, detail="no_items")
```

✅ **Integración con inventario:**
```python
# Al confirmar orden, reserva stock
for it in items:
    mv = StockMove(
        product_id=it.product_id,
        warehouse_id=payload.warehouse_id,
        qty=it.qty,
        kind="reserve",
        tentative=True,
        ref_type="sales_order",
        ref_id=str(order_id),
    )
    db.add(mv)
```

✅ **Entrega de pedidos:**
- `POST /deliveries/` - Crear entrega
- `POST /deliveries/{id}/deliver` - Ejecutar entrega (consume stock real)

### Frontend (TypeScript)
**Ubicación:** `apps/tenant/src/modules/ventas/`

#### Archivos principales:
- `services.ts` - Cliente API
- `Form.tsx` - Formulario
- `List.tsx` - Listado
- `Detail.tsx` - Vista detalle

#### Funcionalidades implementadas:
⚠️ **Tipos mínimos:**
```typescript
export type Venta = {
  id: number | string
  numero?: string
  fecha: string
  cliente_id?: number | string
  total: number
  subtotal?: number
  impuesto?: number
  estado?: string
  lineas?: VentaLinea[]
}
```

❌ **NO hay cálculos** - ✅ BIEN  
❌ **NO hay validaciones** - ✅ BIEN  
✅ **Solo llamadas API** - ✅ CORRECTO

### Duplicaciones Detectadas

| Elemento | Backend | Frontend | Acción |
|----------|---------|----------|--------|
| **Validación de estado** | ✅ Completa | ❌ No existe | ✅ OK |
| **Reserva de stock** | ✅ Completa | ❌ No existe | ✅ OK |
| **Consumo de stock** | ✅ Completa | ❌ No existe | ✅ OK |
| **Cálculo de totales** | ✅ Backend | ❌ Frontend | ✅ OK |

### Recomendación
✅ **Mantener:** Backend  
✅ **Frontend correcto:** Solo UI  
🎯 **Estado ideal:** Este módulo está bien diseñado

---

## 4. PRODUCTOS

### Backend (Python)
**Ubicación:** `apps/backend/app/modules/productos/`

#### Archivos principales:
- `domain/entities.py` - Entidades de dominio
- `application/use_cases.py` - Casos de uso
- `application/ports.py` - Puertos (interfaces)
- `infrastructure/repositories.py` - Repositorios
- `interface/http/tenant.py` - Endpoints

#### Funcionalidades implementadas:
✅ **Arquitectura hexagonal (DDD):**
```python
@dataclass
class Producto:
    id: Optional[int]
    nombre: str
    precio: float
    activo: bool
    tenant_id: int
    
    def validate(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("nombre requerido")
        if self.price < 0:
            raise ValueError("precio no puede ser negativo")
```

✅ **Casos de uso separados:**
- `CrearProducto` - Validación + creación
- `ListarProductos` - Obtención con filtros

✅ **Endpoints REST:**
- `GET /api/v1/tenant/products/`
- `POST /api/v1/tenant/products/`
- `PUT /api/v1/tenant/products/{id}`
- `DELETE /api/v1/tenant/products/{id}`
- `POST /api/v1/tenant/products/bulk/active`
- `POST /api/v1/tenant/products/bulk/category`
- `POST /api/v1/tenant/products/purge`

### Frontend (TypeScript)
**Ubicación:** `apps/tenant/src/modules/productos/`

#### Archivos principales:
- `services.ts` - Cliente API
- `Form.tsx` - Formulario CRUD
- `List.tsx` - Listado con filtros

#### Funcionalidades implementadas:
⚠️ **Normalización compleja:**
```typescript
const norm = (p: any): Producto => {
  return {
    id: String(p.id),
    sku: p.sku ?? null,
    name: p.name,
    description: p.description ?? p.descripcion ?? null,
    price: Number(p.price ?? p.precio ?? 0) || 0,
    precio_compra: p.precio_compra ?? p.cost ?? p.cost_price ?? null,
    iva_tasa: p.iva_tasa ?? p.tax_rate ?? null,
    categoria: p.categoria ?? (typeof p.category === 'string' ? p.category : p.category?.name) ?? null,
    active: Boolean(p.active ?? p.activo ?? true),
    stock: Number(p.stock ?? 0) || 0,
    unit: p.unit || p.uom || 'unit',
  }
}
```

❌ **NO hay validaciones de negocio** - ✅ BIEN (las hace el backend)  
❌ **NO hay cálculos** - ✅ BIEN

### Duplicaciones Detectadas

| Elemento | Backend | Frontend | Acción |
|----------|---------|----------|--------|
| **Validación precio negativo** | ✅ Backend | ❌ Frontend | ✅ OK |
| **Validación nombre requerido** | ✅ Backend | ❌ Frontend | ⚠️ Agregar validación UI para UX |
| **Normalización ES/EN** | ❌ Backend | ⚠️ Frontend compleja | 🔄 Backend debe devolver schema consistente |
| **Mapeo de campos legados** | ❌ No existe | ⚠️ Frontend maneja múltiples formatos | 🔄 Migrar datos legados en DB |

### Recomendación
✅ **Mantener:** Backend con validaciones de dominio  
⚠️ **Migrar a backend:** Normalización de schemas (decidir nombres finales)  
⚠️ **Agregar en frontend:** Validación básica de formularios (UX) pero sin lógica de negocio  
🗑️ **Eliminar del frontend:** La normalización compleja - backend debe devolver datos limpios

---

## 5. POS (PUNTO DE VENTA)

### Backend (Python)
**Ubicación:** `apps/backend/app/modules/pos/`

#### Archivos principales:
- `interface/http/tenant.py` - Endpoints REST (1000+ líneas)

#### Funcionalidades implementadas:
✅ **Gestión de registros POS:**
- `GET/POST /pos/registers`
- Asignación de almacén por defecto

✅ **Gestión de turnos:**
- `POST /pos/shifts` - Abrir turno
- `GET /pos/shifts/{id}/summary` - Resumen con productos vendidos + stock restante
- `POST /pos/shifts/{id}/close` - Cerrar turno

✅ **Recibos (tickets):**
- `POST /pos/receipts` - Crear recibo
- `POST /pos/receipts/{id}/checkout` - Pagar + descontar stock (atómico)
- `GET /pos/receipts/{id}/print` - Generar HTML de impresión

✅ **Cálculos críticos en backend:**
```python
def _to_decimal(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

class ReceiptLineIn(BaseModel):
    qty: float = Field(gt=0)
    unit_price: float = Field(ge=0)
    tax_rate: float = Field(ge=0, le=1, default=0)
    discount_pct: float = Field(ge=0, le=100, default=0)
    
    @property
    def line_total(self) -> float:
        subtotal = self.qty * self.unit_price
        discount = subtotal * (self.discount_pct / 100)
        return subtotal - discount
```

✅ **Integración con impuestos configurables:**
```python
def _resolve_default_tax_rate(db: Session) -> float | None:
    """Obtiene tasa por defecto desde settings"""
    repo = SettingsRepo(db)
    pos_cfg = repo.get("pos") or {}
    return pos_cfg.get("tax", {}).get("default_rate")
```

✅ **Validaciones de pago:**
```python
# Verificar que el pago cubre el total
if paid + 1e-6 < total:
    raise HTTPException(status_code=400, detail="Pago insuficiente")
```

✅ **Descuento de stock atómico:**
```python
# Al hacer checkout, consume stock en un solo paso
for it in items:
    db.execute(text(
        "INSERT INTO stock_moves(...) VALUES (...)"
    ))
    db.execute(text(
        "UPDATE stock_items SET qty = qty - :q WHERE ..."
    ))
```

### Frontend (TypeScript)
**Ubicación:** `apps/tenant/src/modules/pos/`

#### Archivos principales:
- `POSView.tsx` - Vista principal con carrito
- `components/PaymentModal.tsx` - Modal de pago
- `components/TicketCart.tsx` - Carrito de productos
- `services.ts` - Cliente API

#### Funcionalidades implementadas:
🚨 **CÁLCULOS DUPLICADOS EN FRONTEND:**

**En POSView.tsx (líneas 200-216):**
```typescript
const totals = useMemo(() => {
  const subtotal = cart.reduce((sum, item) => sum + item.price * item.qty, 0)
  const lineDiscounts = cart.reduce(
    (sum, item) => sum + item.price * item.qty * (item.discount_pct / 100),
    0
  )
  const baseAfterLineDisc = subtotal - lineDiscounts
  const globalDisc = baseAfterLineDisc * (globalDiscountPct / 100)
  const base = baseAfterLineDisc - globalDisc
  const tax = cart.reduce((sum, item) => {
    const lineBase = item.price * item.qty * (1 - item.discount_pct / 100)
    return sum + lineBase * (item.iva_tasa / 100)
  }, 0)
  const total = base + tax
  return { subtotal, lineDiscounts, globalDisc, base, tax, total }
}, [cart, globalDiscountPct])
```

**En TicketCart.tsx (líneas 15-34):**
```typescript
const calculateTotals = () => {
  let subtotal = 0
  let taxTotal = 0

  items.forEach((item) => {
    const lineSubtotal = (item.qty ?? 0) * (item.unit_price ?? 0)
    const discount = lineSubtotal * ((item.discount_pct ?? 0) / 100)
    const lineNet = lineSubtotal - discount
    const lineTax = lineNet * (item.tax_rate ?? 0)
    subtotal += lineNet
    taxTotal += lineTax
  })

  return {
    subtotal: subtotal.toFixed(2),
    taxTotal: taxTotal.toFixed(2),
    total: (subtotal + taxTotal).toFixed(2)
  }
}
```

🚨 **VALIDACIONES EN FRONTEND (PaymentModal.tsx):**
```typescript
const toNumber = (v: string | number): number => {
  if (typeof v === 'number') return v
  const normalized = String(v).trim().replace(/\s+/g, '').replace(',', '.')
  const n = parseFloat(normalized)
  return Number.isFinite(n) ? n : 0
}

const handlePay = async () => {
  // Validación de pago insuficiente EN FRONTEND
  const paid = toNumber(cashAmount)
  const paidCents = Math.round(paid * 100)
  const totalCents = Math.round(totalAmount * 100)
  if (paidCents < totalCents) {
    const faltante = ((totalCents - paidCents) / 100).toFixed(2)
    alert(`El importe recibido es insuficiente. Falta ${currencySymbol}${faltante}.`)
    return
  }
}
```

⚠️ **Cálculo de cambio en frontend:**
```typescript
const calculateChange = () => {
  if (paymentMethod === 'cash') {
    const paid = toNumber(cashAmount)
    return Math.max(0, paid - totalAmount)
  }
  return 0
}
```

### Duplicaciones Detectadas

| Elemento | Backend | Frontend | Peligro | Acción |
|----------|---------|----------|---------|--------|
| **Cálculo de subtotal con descuentos** | ✅ `line_total` | 🚨 `POSView.totals` | ⚠️ ALTO | 🗑️ Eliminar de frontend |
| **Cálculo de impuestos** | ✅ `tax_rate * base` | 🚨 Dos implementaciones | ⚠️ ALTO | 🗑️ Eliminar de frontend |
| **Validación pago insuficiente** | ✅ Backend checkout | 🚨 `PaymentModal` | ⚠️ MEDIO | 🗑️ Eliminar de frontend |
| **Cálculo de cambio** | ❌ No existe | ⚠️ `calculateChange()` | ✅ OK | Mantener (UI local) |
| **Redondeo de decimales** | ✅ `Decimal.quantize()` | ⚠️ `toFixed(2)` | ⚠️ BAJO | Puede diferir |
| **Descuento de stock** | ✅ Atómico SQL | ❌ No existe | ✅ OK | - |

### Recomendación
🚨 **CRÍTICO - Migrar a backend:**
1. **Cálculo de totales del carrito** - El frontend NO debería calcular subtotales, descuentos ni impuestos
2. **Validación de pago insuficiente** - El backend ya lo hace, remover del frontend

⚠️ **Mantener en frontend:**
- Cálculo de cambio (solo para UI, no afecta transacción)
- Validación básica de campos vacíos (UX)

✅ **Correcto en backend:**
- Todas las validaciones críticas
- Descuento atómico de stock
- Cálculo con Decimal para evitar errores de punto flotante

🔄 **Propuesta de refactor:**
```typescript
// ANTES (frontend calcula todo)
const totals = useMemo(() => {
  const subtotal = cart.reduce(...)
  const tax = cart.reduce(...)
  return { subtotal, tax, total }
}, [cart])

// DESPUÉS (backend calcula, frontend muestra)
const [totals, setTotals] = useState({ subtotal: 0, tax: 0, total: 0 })

useEffect(() => {
  if (cart.length > 0) {
    calculateReceiptTotals({ lines: cart }).then(setTotals)
  }
}, [cart])
```

---

## RESUMEN GENERAL

### Módulos con arquitectura correcta ✅
1. **Ventas** - Backend maneja toda la lógica, frontend solo UI
2. **Facturación** - Solo enums de UI en frontend (aceptable)

### Módulos que necesitan ajustes ⚠️
1. **Inventario** - Normalización ES/EN debería estar en backend
2. **Productos** - Normalización de schemas legados en frontend

### Módulos con duplicaciones críticas 🚨
1. **POS** - Cálculos de totales, descuentos e impuestos duplicados en frontend

---

## PRIORIDADES DE CORRECCIÓN

### 🔴 URGENTE (Seguridad/Consistencia)
1. **POS: Eliminar cálculos de totales del frontend**
   - Endpoint: `POST /api/v1/pos/receipts/calculate_totals`
   - Input: `{ lines: [...], global_discount_pct?: number }`
   - Output: `{ subtotal, tax, total, line_discounts, global_discount }`

2. **POS: Remover validación de pago en frontend**
   - El backend ya valida en `/checkout`
   - Frontend solo debe mostrar mensajes de error del backend

### 🟡 MEDIA (Mantenibilidad)
3. **Backend: Estandarizar nombres de campos (ES vs EN)**
   - Decidir: `name` o `nombre`, `price` o `precio`
   - Actualizar modelos SQLAlchemy y Pydantic
   - Migración de datos si es necesario

4. **Backend: Endpoint de configuración de enums**
   - `GET /api/v1/config/enums` devuelve:
     ```json
     {
       "invoice_statuses": ["draft", "sent", "paid", "overdue", "cancelled"],
       "stock_move_kinds": ["purchase", "sale", "adjustment", "transfer"],
       "payment_methods": ["cash", "card", "store_credit", "link"]
     }
     ```

### 🟢 BAJA (Optimización)
5. **Frontend: Validaciones de UX (sin lógica de negocio)**
   - Validar campos requeridos antes de enviar
   - Validar formatos (email, teléfono)
   - Validar rangos razonables (precio > 0)
   - NUNCA validar reglas de negocio complejas

6. **Documentación de API**
   - OpenAPI/Swagger con ejemplos
   - Especificar exactamente qué validaciones hace el backend
   - Guías de integración para frontend

---

## CONSTANTES/ENUMS DETECTADOS

### Deberían venir del backend:

#### Facturación
```typescript
// Frontend hardcoded - debería ser dinámico
const INVOICE_STATUSES = ['draft', 'sent', 'paid', 'overdue', 'cancelled']
const EINVOICE_STATUSES = ['PENDING', 'SENT', 'AUTHORIZED', 'REJECTED', 'ERROR']
```

#### Inventario
```typescript
// Frontend hardcoded - debería ser dinámico
const STOCK_MOVE_KINDS = ['purchase', 'sale', 'adjustment', 'transfer', 'production', 'return', 'loss']
```

#### POS
```typescript
// Frontend hardcoded - debería ser dinámico
const PAYMENT_METHODS = ['cash', 'card', 'store_credit', 'link']
```

---

## MÉTRICAS DE DUPLICACIÓN

| Módulo | Archivos Backend | Archivos Frontend | Lógica duplicada | Severidad |
|--------|------------------|-------------------|------------------|-----------|
| Facturación | 8 | 12 | Enums UI | 🟢 Baja |
| Inventario | 1 | 18 | Normalización | 🟡 Media |
| Ventas | 3 | 10 | Ninguna | ✅ OK |
| Productos | 13 | 9 | Normalización | 🟡 Media |
| POS | 1 (1000 líneas) | 18 | **Cálculos + Validaciones** | 🔴 Alta |

---

## PLAN DE ACCIÓN RECOMENDADO

### Fase 1: Corrección crítica (POS)
1. Crear endpoint `POST /pos/receipts/calculate_totals`
2. Refactor frontend para usar endpoint de cálculo
3. Eliminar `calculateTotals()` de `POSView.tsx` y `TicketCart.tsx`
4. Eliminar validación de pago insuficiente en `PaymentModal.tsx`
5. Testing exhaustivo de casos edge (redondeos, descuentos múltiples)

### Fase 2: Normalización de schemas
1. Auditar todos los modelos SQLAlchemy
2. Decidir nomenclatura estándar (EN recomendado)
3. Actualizar Pydantic schemas
4. Actualizar tipos TypeScript
5. Eliminar normalizadores en `productos/services.ts` e `inventario/services.ts`

### Fase 3: Centralización de configuración
1. Crear tabla `system_config` en DB
2. Endpoint `GET /api/v1/config` con enums, constantes
3. Actualizar frontend para consumir configuración dinámica
4. Eliminar constantes hardcoded en TypeScript

### Fase 4: Validaciones de UX (opcional)
1. Agregar validaciones de formulario en frontend (solo UX)
2. Documentar claramente que NO son validaciones de negocio
3. Siempre confiar en las validaciones del backend

---

## CONCLUSIONES

### ✅ Aspectos positivos:
- **Ventas** y **Facturación** tienen buena separación de responsabilidades
- Backend implementa validaciones consistentes
- No se detectaron cálculos de negocio críticos en frontend (excepto POS)

### 🚨 Aspectos críticos:
- **POS tiene lógica de cálculo duplicada** - puede generar inconsistencias
- La validación de pago en frontend puede ser burlada (aunque backend re-valida)
- Riesgo de errores de redondeo (JS `Number` vs Python `Decimal`)

### ⚠️ Aspectos mejorables:
- Normalización de schemas (ES/EN) genera código complejo en frontend
- Enums hardcoded dificultan cambios de configuración
- Falta documentación clara de qué valida cada capa

### 🎯 Estado objetivo:
```
┌─────────────────────────────────────────────────────┐
│ FRONTEND (TypeScript)                               │
│ - Solo UI y validaciones de UX                      │
│ - Tipos reflejan el schema del backend              │
│ - Consume configuración dinámica                    │
│ - NO calcula totales, descuentos, impuestos         │
└─────────────────────────────────────────────────────┘
                       ▲
                       │ REST API (solo lectura de cálculos)
                       │
┌─────────────────────────────────────────────────────┐
│ BACKEND (Python)                                    │
│ - Toda la lógica de negocio                         │
│ - Validaciones de dominio                           │
│ - Cálculos con Decimal (precisión)                  │
│ - Operaciones atómicas en DB                        │
│ - Configuración centralizada                        │
└─────────────────────────────────────────────────────┘
```

---

**Generado:** 2025-11-05  
**Próxima revisión:** Después de implementar correcciones en POS
