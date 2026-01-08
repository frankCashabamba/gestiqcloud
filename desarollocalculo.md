# desarollo.md - Margenes y Beneficio por Producto (POS/ERP)

## Estado actual (actualizado)
### Hecho
- Migraciones para `stock_moves` (costos) + `pos_receipts.warehouse_id` + snapshot en `pos_receipt_lines` + tabla `inventory_cost_state`.
- Servicio WAC aplicado en inventario (ajustes, transferencias, conteo), compras (recepcion), ventas (checkout POS y delivery) e importaciones de stock (si aplica).
- Checkout POS calcula y congela `net_total`, `cogs_*`, `gross_*` por linea y crea `stock_moves` con costo.
- Reembolso POS completo: lineas negativas + reposicion de stock + `stock_moves` de devolucion.
- Endpoints analiticos: margen por producto, cliente y drill-down por lineas.
- Frontend UI de reportes integrado (rutas, estilos y dashboard).
- Preparacion IVA: campos `tax_total`/`gross_total` ya existen en DB y modelos.
- Tests: smoke POS + WAC basico + analytics de margenes.

### Pendiente (opcional)
- Tests de concurrencia (dos ventas simultaneas mismo producto) si se desea validar locking a nivel DB.
- Notas de credito parciales o referenciadas (fuera del alcance del MVP).

## 0) Contexto [HECHO]
El sistema ya tiene:
- Modulo **Productos**
- Modulo **Inventario** con `stock_items` y `stock_moves`
- Modulo **POS** con `pos_receipts`, `pos_receipt_lines`, `pos_payments`

Objetivo: anadir **margen/beneficio profesional** (Gross Profit) por producto/cliente/periodo, empezando **SIN IVA** (IVA configurable pero actualmente no se usa en calculo).

---

## 1) Objetivo principal [HECHO]
Calcular y persistir (congelar) en cada **linea de venta**:
- Ventas netas (sin IVA)
- Costo de lo vendido (COGS)
- Beneficio bruto (Gross Profit)
- Margen bruto %

Y poder generar reportes rapidos y consistentes:
- Margen por producto
- Margen por cliente
- Margen por periodo
- Alertas de margen bajo/negativo

> Regla clave: **NO recalcular historicos al vuelo**. El costo aplicado a cada venta debe guardarse al "postear/cerrar" el ticket.

---

## 2) Definiciones [HECHO]
### 2.1 Formulas (SIN IVA)
- `net_total = qty * unit_price * (1 - discount_pct/100)`
- `cogs_unit = costo unitario aplicado en el momento de vender`
- `cogs_total = qty * cogs_unit`
- `gross_profit = net_total - cogs_total`
- `gross_margin_pct = gross_profit / net_total` (si `net_total > 0`, si no `0`)

### 2.2 Que es "COGS" [HECHO]
COGS (Cost of Goods Sold) = costo de inventario consumido por la venta.
Se calcula con metodo **Promedio Ponderado** (Weighted Average Cost, WAC).

---

## 3) Decisiones de diseno [HECHO]
1) El margen se calcula **cuando el receipt pasa a `paid`** (o estado equivalente "posted/confirmed").
2) Se deben guardar los campos de margen en `pos_receipt_lines` (snapshot).
3) Para que el COGS sea auditable, `stock_moves` debe guardar `unit_cost` y `total_cost`.
4) Se necesita conocer el **warehouse** usado en la venta.
   - `warehouse_id` en `pos_receipts`.
   - Decision: se mantiene nullable en draft; en paid/invoiced siempre se setea en checkout.
5) Manejo de IVA: por ahora **no se usa**; se deja preparado para el futuro.

---

## 4) Cambios en Base de Datos (Migraciones) [HECHO]

### 4.1 `stock_moves`: guardar costo
Agregar columnas:
- `unit_cost NUMERIC(12,6) NULL`
- `total_cost NUMERIC(14,6) NULL`
- `occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()` (si no existe)
- (opcional) index por `tenant_id, warehouse_id, product_id, occurred_at`

Motivo:
- En entradas: costo proviene de compra/ajuste.
- En salidas: costo se fija segun WAC en el momento de vender.

### 4.2 `pos_receipts`: anadir warehouse_id (recomendado)
Agregar:
- `warehouse_id UUID` (se asigna en checkout; draft puede quedar null)
Origen:
- Puede derivar del `register` o configurarse al crear el receipt.

### 4.3 `pos_receipt_lines`: snapshot financiero + margen
Agregar columnas:
- `net_total NUMERIC(12,2) NOT NULL DEFAULT 0`
- `cogs_unit NUMERIC(12,6) NOT NULL DEFAULT 0`
- `cogs_total NUMERIC(12,2) NOT NULL DEFAULT 0`
- `gross_profit NUMERIC(12,2) NOT NULL DEFAULT 0`
- `gross_margin_pct NUMERIC(7,4) NOT NULL DEFAULT 0`

> Mantener `tax_rate` por compatibilidad, pero por ahora no usar.

### 4.4 Tabla nueva: `inventory_cost_state` (estado WAC)
Crear tabla para evitar recalcular costos desde historico cada vez:

```sql
CREATE TABLE inventory_cost_state (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  warehouse_id uuid NOT NULL,
  product_id uuid NOT NULL,
  on_hand_qty numeric NOT NULL DEFAULT 0,
  avg_cost numeric(12,6) NOT NULL DEFAULT 0,
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, warehouse_id, product_id)
);
```

---

## 5) Logica de Costeo: Promedio Ponderado (WAC) [HECHO]

### 5.1 Entrada de stock (compras/ajustes positivos)
Al postear un movimiento de entrada:
- `in_qty > 0`
- `in_unit_cost >= 0`

Actualizar estado:
- `new_qty = old_qty + in_qty`
- `new_avg = (old_qty * old_avg + in_qty * in_unit_cost) / new_qty`  (si `new_qty > 0`)
- Guardar en `inventory_cost_state`:
  - `on_hand_qty = new_qty`
  - `avg_cost = new_avg`

Persistir en `stock_moves`:
- `unit_cost = in_unit_cost`
- `total_cost = in_qty * in_unit_cost`

### 5.2 Salida de stock (ventas)
Al postear venta:
- Leer `avg_cost` actual de `inventory_cost_state` con **lock** (FOR UPDATE).
- `cogs_unit = avg_cost`
- `cogs_total = sold_qty * cogs_unit`
- Reducir `on_hand_qty = old_qty - sold_qty`
  - Politica: bloquear venta si no hay stock suficiente (MVP).

Persistir en `stock_moves` OUT:
- `qty` negativa o `kind="out"` con qty positiva (definir convencion)
- `unit_cost = cogs_unit`
- `total_cost = cogs_total`

> **Importante**: `avg_cost` no cambia en la salida; solo cambia en entradas.

---

## 6) Flujo de "Postear/Pagar" POSReceipt (punto de calculo de margen) [HECHO]

### 6.1 Trigger de negocio
Cuando `pos_receipts.status` cambie de `draft` -> `paid` (o equivalente):
- Iniciar transaccion DB.
- Lock del receipt.
- Para cada linea:
  1. Convertir cantidad a unidad base si aplica UoM (si existe)
  2. Calcular `net_total`
  3. Obtener `cogs_unit` via WAC (`inventory_cost_state` con FOR UPDATE)
  4. Calcular `cogs_total`, `gross_profit`, `gross_margin_pct`
  5. Guardar snapshot en `pos_receipt_lines`
  6. Crear `stock_move` de salida con `unit_cost/total_cost` y `ref_type/ref_id`

- Marcar receipt como `paid` y `paid_at`.

### 6.2 Precision numerica
Usar `Decimal` en backend para calculos:
- `unit_price` y `cogs_unit` con 4-6 decimales
- totales monetarios redondeados a 2 decimales (EUR)

Definir regla de redondeo (ej. bankers rounding o HALF_UP) y aplicarla consistentemente.

---

## 7) Reportes/Endpoints de Analitica (MVP) [HECHO]

### 7.1 Margen por producto
Endpoint actual:
- `GET /api/v1/tenant/pos/analytics/margins/products?from=YYYY-MM-DD&to=YYYY-MM-DD&warehouse_id=...&limit=...`

### 7.2 Margen por cliente
Endpoint actual:
- `GET /api/v1/tenant/pos/analytics/margins/customers?...`

### 7.3 Drill-down
- `GET /api/v1/tenant/pos/analytics/margins/product/{product_id}/lines?...` para ver las lineas que componen el margen.

---

## 8) UI/UX (para "sorprender") [HECHO]
### 8.1 Dashboard
Cards:
- Ventas netas
- COGS
- Beneficio bruto
- Margen bruto %
- Top 5 productos por beneficio / Peor 5 por margen

### 8.2 Tabla "Margen por Producto"
Columnas:
- Producto
- Unidades vendidas
- Ventas netas
- COGS
- Beneficio bruto
- Margen %
- Precio medio
- Costo medio aplicado

### 8.3 Alertas
- Margen % < X
- Beneficio bruto negativo
- Precio minimo recomendado:
  - `min_price = cogs_unit / (1 - target_margin)` (si target_margin < 1)

---

## 9) Casos especiales y politicas [HECHO]

### 9.1 Stock insuficiente
Politica MVP:
- Bloquear venta si `on_hand_qty < qty`.

### 9.2 Devoluciones / notas de credito
- Reembolso completo POS implementado con lineas negativas y reposicion de stock.
- Notas de credito parciales quedan fuera del MVP.

### 9.3 Cambios manuales de precio
Permitido:
- `unit_price` puede variar por linea
- El margen se calcula con el precio final (net_total) y el cogs_unit aplicado

---

## 10) Preparacion futura para IVA (no implementar ahora) [HECHO]
- Mantener `tax_rate` como campo "snapshot"
- Campos `tax_total` y `gross_total` ya existen en line/receipt
- Flag `tenant.prices_include_tax` quedara para una fase fiscal futura
- **El margen sigue basandose en net_total**.

---

## 11) Plan de implementacion (pasos) [HECHO]
1) Migraciones DB
2) Backend (WAC + POS + inventario + compras)
3) Endpoints de analitica
4) Frontend
5) Tests

---

## 12) Criterios de aceptacion (Definition of Done) [HECHO]
- Al pagar un receipt:
  - Se guardan `net_total`, `cogs_*`, `gross_*` en cada linea
  - Se crea `stock_move` out con `unit_cost` y `total_cost`
  - El stock disminuye correctamente y el costo WAC se respeta
- Reporte "Margen por producto" coincide con sumas de lineas posteadadas
- Historicos no cambian aunque cambie el costo futuro del producto
- Manejo correcto de descuento (discount_pct)

---

## 13) Notas de implementacion (SQLAlchemy / FastAPI) [HECHO]
- Usar `Decimal` en calculo, convertir a NUMERIC.
- En queries criticas usar `SELECT ... FOR UPDATE` sobre `inventory_cost_state`.
- Asegurar siempre filtro `tenant_id` (multi-tenant).
- No usar `float` para dinero.

---

## 14) Convenciones recomendadas [HECHO]
- `StockMove.kind`: `in`, `out`, `adjust`, `transfer`
- `StockMove.qty`: definir si out es negativo o qty positiva + kind.
  - Recomendado: qty positiva siempre y `kind` define signo logico (mas claro).
- `ref_type/ref_id`: `pos_receipt`, `purchase`, etc. para auditoria.

---
