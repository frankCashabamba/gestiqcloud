# Módulo POS (Terminal Punto de Venta) - Documentación

## 📋 Descripción

Terminal profesional de punto de venta (TPV) con diseño oscuro optimizado para uso intensivo. Integrado con inventario, productos, pagos y facturación.

## 🏗️ Arquitectura

```
apps/tenant/src/modules/pos/
├── POSView.tsx (420 líneas)       ✅ Vista principal con diseño tpv_pro.html
├── pos-styles.css                  ✅ Estilos profesionales dark mode
├── components/                     ✅ 9 componentes
│   ├── ShiftManager.tsx            ✅ Gestión de turnos
│   ├── TicketCart.tsx              ✅ Carrito avanzado
│   ├── PaymentModal.tsx            ✅ Modal de cobro multi-método
│   ├── ConvertToInvoiceModal.tsx   ✅ Ticket → Factura
│   ├── BarcodeScanner.tsx          ✅ Scanner cámara
│   ├── WeightInput.tsx             ✅ Productos a peso
│   ├── RefundModal.tsx             ✅ Devoluciones
│   ├── StoreCreditsModal.tsx       ✅ Vales
│   └── StoreCreditsList.tsx        ✅ Gestión vales
├── hooks/
│   └── useOfflineSync.tsx          ✅ Sync offline-lite
├── services.ts                     ✅ API client completo
├── Routes.tsx                      ✅ Rutas
├── manifest.ts                     ✅ Config módulo
└── tpv_pro.html                    ✅ Prototipo de diseño
```

**Backend:**
```
apps/backend/app/modules/pos/interface/http/tenant.py (900+ líneas)
✅ 13 endpoints completos
✅ Integración automática con inventario
✅ Numeración automática de tickets
```

---

## ✨ Características principales

### **1. Diseño Profesional (Basado en tpv_pro.html)**

#### Layout
```
┌─────────────────────────────────────────────────────────────┐
│ 🛒 TPV - GestiQCloud │ Online │ Caja: Principal            │ TOP
├─────────────────────────────────┬───────────────────────────┤
│                                 │                           │
│  🔍 Buscar | EAN | Limpiar      │  CARRITO                 │
│                                 │  ───────────────────────  │
│  [Todo] [Pan] [Bollería]        │  Pan integral  [- 3 +]   │
│                                 │  2.50€         7.50€  ✕  │
│  ┌────┐ ┌────┐ ┌────┐          │                           │
│  │Pan │ │Bag │ │Croi│          │  Subtotal:      7.50€    │
│  │1.2€│ │1.3€│ │1.1€│   LEFT   │  Descuento:    -0.00€    │ RIGHT
│  └────┘ └────┘ └────┘          │  IVA:           0.75€    │
│  ┌────┐ ┌────┐ ┌────┐          │  TOTAL:        8.25€     │
│  │Café│ │...│  │...│           │                           │
│  └────┘ └────┘ └────┘          │  [Efectivo] [Tarjeta]    │
│                                 │  [Mixto] [Abrir cajón]   │
└─────────────────────────────────┴───────────────────────────┤
│ [Borrar todo] [Notas]           [COBRAR 8.25€]            │ BOTTOM
└─────────────────────────────────────────────────────────────┘
```

#### Características visuales:
- ✅ **Dark mode profesional** (#0b0e14)
- ✅ **Grid responsivo** 6/4/3 columnas (desktop/tablet/mobile)
- ✅ **Tiles hover animados** (transform + shadow)
- ✅ **Badges de estado** (Online/Offline con colores)
- ✅ **Teclado numérico** para efectivo
- ✅ **Separación visual clara** (left catalog / right cart)

---

### **2. Gestión de Turnos**

```typescript
✅ Abrir turno:
   - Seleccionar caja/registro
   - Fondo inicial (opening_float)
   - Usuario asignado

✅ Durante turno:
   - Ventas normales
   - Ver total acumulado
   - No se puede vender sin turno abierto

✅ Cerrar turno:
   - Arqueo de caja (contar efectivo)
   - Total esperado vs real
   - Diferencias reportadas
   - Genera reporte PDF/Excel
```

**Backend:**
```python
POST /api/v1/tenant/pos/shifts
POST /api/v1/tenant/pos/shifts/:shift_id/close
GET  /api/v1/tenant/pos/shifts/current/:register_id
```

---

### **3. Catálogo de Productos**

#### Grid de 6 columnas responsive
```tsx
✅ Productos activos desde módulo Productos
✅ Tile con:
   - Nombre (strong)
   - Precio (small)
   - Tags opcionales (popular, rápido, ahorro)

✅ Click = añadir al carrito
✅ Hover animado (elevación + shadow)
✅ Adaptable a 3 sectores:
   - Panadería: Pan, Bollería, Pastelería
   - Retail: Ropa, Electrónica, Hogar
   - Taller: Repuestos, Mano Obra, Servicios
```

#### Búsqueda dual
```tsx
✅ Input texto: busca por nombre/SKU
✅ Input barcode: busca por EAN/código de barras
✅ Enter en barcode = añade al carrito automáticamente
✅ F2 = focus en búsqueda (atajo teclado)
```

#### Filtro por categorías
```tsx
✅ Botones dinámicos según categorías de productos
✅ "Todo" = muestra todos
✅ Click categoría = filtra productos
✅ Categorías se cargan automáticamente de:
   - producto.categoria
   - producto.product_metadata.categoria
```

---

### **4. Carrito de Compra**

#### Líneas de venta
```tsx
✅ Grid 4 columnas: [Producto | Qty | Total | Delete]
✅ Controles por línea:
   - [- qty +] Incrementar/decrementar
   - [-% ] Descuento específico de línea
   - [📝 ] Notas de línea
   - [✕ ] Eliminar
```

#### Cálculos automáticos
```typescript
Subtotal = Σ (precio × qty)
Desc. línea = Σ (precio × qty × discount_pct)
Base después línea = Subtotal - Desc. línea
Desc. global = Base × globalDiscountPct
Base final = Base después línea - Desc. global
IVA = Σ (base_línea × iva_tasa)
TOTAL = Base final + IVA
```

---

### **5. Métodos de Pago (Multi-método)**

#### **Efectivo**
```tsx
✅ Input entregado con teclado numérico
✅ Cálculo automático de cambio
✅ Teclas especiales:
   [⌫] Borrar último dígito
   [×2] Duplicar cantidad
   [%] Añadir 10% propina
   [Exacto] Importe exacto del total
   [Borrar] Limpiar input
   [0-9, ,] Números y coma decimal
```

#### **Tarjeta**
```tsx
✅ Botón "Iniciar TPV Tarjeta"
✅ Integración con pinpad (simulada)
✅ Conexión RedSys/Stripe (en desarrollo)
```

#### **Pago Mixto**
```tsx
✅ Input efectivo
✅ Input tarjeta
✅ Muestra pendiente: Total - (Efectivo + Tarjeta)
✅ Validación: suma debe >= total
```

#### **Vales/Store Credits**
```tsx
✅ Input código vale
✅ Validación automática
✅ Descuenta del total
✅ Actualiza vale.amount_remaining
```

---

### **6. Integración con Inventario (Automática)**

#### Al finalizar venta (POST receipt):

```python
# Backend crea automáticamente:

1. stock_move por cada línea:
   INSERT INTO stock_moves(
     product_id,
     warehouse_id,
     qty,  # Cantidad vendida
     kind='issue',  # Salida
     ref_type='pos_receipt',
     ref_id=receipt.id
   )

2. Actualiza stock_items:
   UPDATE stock_items
   SET qty = qty - vendido
   WHERE product_id = ? AND warehouse_id = ?

3. Si no existe stock_item, lo crea con qty=0
```

**✅ RESULTADO:** Stock se reduce automáticamente sin intervención manual

---

### **7. Impresión Térmica (58mm/80mm)**

#### Endpoint backend ya operativo:
```python
GET /api/v1/tenant/pos/receipts/{id}/print?width=58mm
GET /api/v1/tenant/pos/receipts/{id}/print?width=80mm
```

#### Plantillas HTML profesionales:
```html
✅ apps/backend/app/templates/pos/ticket_58mm.html
✅ apps/backend/app/templates/pos/ticket_80mm.html

Contenido:
- Nombre empresa
- Número ticket
- Fecha/hora
- Líneas de venta (producto, qty, precio)
- Subtotal, IVA desglosado, Total
- Método de pago
- Código QR (para devoluciones)
```

#### Impresión automática:
```typescript
✅ Al completar pago, abre window.open() con HTML
✅ Usuario hace Ctrl+P (system print)
✅ Compatible con impresoras ESC/POS vía navegador
```

---

### **8. Ticket → Factura**

```typescript
✅ Modal ConvertToInvoiceModal
✅ Captura:
   - NIF/RUC/Cédula
   - Nombre cliente
   - Dirección (opcional)

✅ Backend crea:
   - Invoice vinculada
   - pos_receipts.invoice_id = invoice.id
   - Numeración automática (doc_series)

✅ Envío e-factura (opcional):
   - España: Facturae
   - Ecuador: SRI XML
```

---

### **9. Devoluciones con Vales**

```typescript
✅ RefundModal
✅ Escanear QR/código de ticket original
✅ Seleccionar líneas a devolver
✅ Método de reembolso:
   - Efectivo
   - Tarjeta (mismo método original)
   - Vale/Store Credit

✅ Backend:
   - Crea invoice negativa (abono)
   - Genera stock_move con qty positivo (devuelto a stock)
   - Actualiza stock_items
   - Genera store_credit si aplica
```

---

### **10. Offline-Lite**

```typescript
✅ Hook useOfflineSync()
✅ Detección automática de conectividad
✅ Badge visual Online/Offline
✅ Cola de sincronización (outbox):
   - POST/PUT → localStorage
   - Sync automático al recuperar conexión
   - Contador pendientes visible
   - Botón sync manual
```

---

## 🎯 Adaptación por Sector

### **PANADERÍA**
```typescript
Categorías: Pan, Bollería, Pastelería, Bebidas, Salado, Combos
Productos a peso: ✅ WeightInput integrado
Caducidades: Muestra lotes del día con prioridad
Layout: Grid 6 columnas (productos visibles)
```

### **RETAIL/BAZAR**
```typescript
Categorías: Ropa, Electrónica, Hogar, Juguetes, etc.
Productos con variantes: Talla/Color en product_metadata
Scanner EAN: ✅ Esencial para retail
Layout: Grid 6 columnas (SKU + nombre + precio)
```

### **TALLER MECÁNICO**
```typescript
❌ NO usa POS (usa presupuestos y facturas tradicionales)
Layout: N/A
```

**🎯 DISEÑO ÚNICO PARA LOS 3 SECTORES:**
El diseño es **universal**. Solo cambian:
- Categorías (dinámicas desde productos)
- Campos visibles en tiles (name + price siempre)
- Tags opcionales (populares, rápidos, etc.)

---

## 🔧 Backend - Endpoints

### Base URL: `/api/v1/tenant/pos`

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/registers` | Lista cajas/registros |
| POST | `/shifts` | Abrir turno |
| POST | `/shifts/:shift_id/close` | Cerrar turno |
| GET | `/shifts/current/:register_id` | Turno actual |
| POST | `/receipts` | Crear ticket |
| POST | `/receipts/:id/checkout` | Cobro + descuento stock (backend) |
| POST | `/receipts/:id/post` | Finalizar (actualiza inventario) |
| GET | `/receipts/:id/print?width=58mm` | HTML impresión |
| POST | `/receipts/:id/to_invoice` | Convertir a factura |
| POST | `/receipts/:id/refund` | Devolución |

---

## 🧪 Testing

### TEST 1: Abrir Turno

1. Acceder a http://localhost:8082/kusi-panaderia/pos
2. Ver componente ShiftManager
3. Click "Abrir turno"
4. Input fondo inicial: 100€
5. Confirmar

**Resultado esperado:**
- Badge verde "Turno abierto"
- Botón "Cobrar" activado

### TEST 2: Añadir Productos al Carrito

1. Buscar "pan"
2. Click en tile "Pan integral 400g"
3. Verificar que aparece en carrito derecho
4. Qty = 1, Total = 2.50€

**Resultado esperado:**
- Línea en carrito
- Totales actualizados

### TEST 3: Scanner de Código de Barras

1. Input "Código de barras"
2. Escribir EAN del producto
3. Pulsar Enter

**Resultado esperado:**
- Producto se añade automáticamente
- Input se limpia

### TEST 4: Modificar Cantidad

1. Click botón [+] en línea de carrito
2. Verificar qty = 2
3. Verificar total = 2.50€ × 2 = 5.00€

### TEST 5: Descuento por Línea

1. Click [-% ] en una línea
2. Input: 10
3. Aceptar

**Resultado esperado:**
- Muestra "Desc 10%"
- Total línea: 2.50€ × 3 × 0.9 = 6.75€

### TEST 6: Descuento Global

1. Click "Descuento" en top bar
2. Input: 5
3. Aceptar

**Resultado esperado:**
- Descuento se aplica sobre base después de desc. línea
- Totales actualizados

### TEST 7: Cobro Efectivo

1. Carrito con total 8.25€
2. Click "Cobrar"
3. Modal de pago se abre
4. Seleccionar "Efectivo"
5. Input entregado: 10€
6. Verificar cambio: 1.75€
7. Click "Confirmar"

**Resultado esperado:**
- Ticket creado
- Stock reducido automáticamente
- Ventana de impresión se abre
- Carrito se vacía

### TEST 8: Filtrar por Categoría

1. Click categoría "Bollería"
2. Verificar que solo se muestran productos de esa categoría
3. Click "Todo"
4. Verificar que se muestran todos

### TEST 9: Integración con Inventario

**Prerequisito:** Producto con stock = 100

1. Vender 3 unidades desde POS
2. Ir a módulo Inventario
3. Buscar el producto

**Resultado esperado:**
- Stock = 97
- Movimiento de tipo "sale" visible
- ref_type = "pos_receipt"

### TEST 10: Ticket → Factura

1. Completar venta
2. En modal de pago, click "Convertir a factura"
3. Input NIF cliente
4. Input nombre cliente
5. Confirmar

**Resultado esperado:**
- Invoice creada
- pos_receipts.invoice_id vinculado
- Factura visible en módulo Facturación

---

## 📊 KPIs del Día (Dashboard - En desarrollo)

```typescript
{
  ventas_hoy: 42,
  importe_total: 1250.50,
  ticket_promedio: 29.77,
  items_vendidos: 156,
  devoluciones: 2,
  turnos_cerrados: 1,
  efectivo_en_caja: 850.00,
  tarjeta: 400.50
}
```

---

## 🔄 Flujo Completo de Venta

```
1. ABRIR TURNO
   Cajera abre turno → Fondo inicial 100€

2. BUSCAR PRODUCTO
   Cliente: "Quiero 3 panes"
   Cajera: Busca "pan" o escanea EAN

3. AÑADIR A CARRITO
   Click en "Pan integral 400g"
   Incrementa qty a 3

4. APLICAR DESCUENTO (opcional)
   Cliente habitual: -10% en esa línea

5. COBRAR
   Click "Cobrar 7.50€"
   Modal se abre

6. SELECCIONAR MÉTODO
   "Efectivo"
   Input: 10€
   Cambio: 2.50€

7. CONFIRMAR
   Backend:
   - Crea pos_receipt
   - Crea stock_move (qty: -3)
   - Actualiza stock_items (100 → 97)
   - Genera número de ticket

8. IMPRIMIR
   Ventana se abre con HTML 58mm
   Cajera: Ctrl+P

9. SIGUIENTE CLIENTE
   Carrito limpio
   Proceso reinicia
```

---

## 🚀 Mejoras V1.1 (Futuro)

- [ ] Dashboard del día con gráficos
- [ ] Tickets en espera (hold/resume)
- [ ] Clientes frecuentes (favoritos)
- [ ] Atajos de teclado (F1-F12)
- [ ] Productos favoritos / más vendidos
- [ ] Multi-almacén (seleccionar warehouse)
- [ ] Balanza integrada (serial port)
- [ ] Impresora térmica directa (ESC/POS vía TCP 9100)

---

**Versión:** 1.0.0
**Estado:** Activo (validar cobertura con tests en CI)
**Última revisión documental:** Febrero 2026
**Sectores soportados:** Panadería, Retail/Bazar
