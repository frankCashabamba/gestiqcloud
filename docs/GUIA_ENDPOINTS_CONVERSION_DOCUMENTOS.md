# 📘 GUÍA DE USO - ENDPOINTS DE CONVERSIÓN DE DOCUMENTOS

## 🎯 Descripción General

Los nuevos endpoints de conversión permiten transformar documentos comerciales entre tipos, manteniendo trazabilidad completa y relaciones bidireccionales.

### Conversiones Disponibles

1. **Orden de Venta → Factura** (`SalesOrder → Invoice`)
2. **Recibo POS → Factura Formal** (`POSReceipt → Invoice`)
3. **Presupuesto → Orden de Venta** (futuro)

---

## 1️⃣ ORDEN DE VENTA → FACTURA

### Caso de Uso
Cliente realiza pedido → Se confirma la orden → Se entrega → **Se factura**

### Endpoint

```http
POST /api/v1/tenant/sales_orders/{order_id}/invoice
Content-Type: application/json
Authorization: Bearer {token}

{
  "payment_terms": "30 days",
  "notes": "Cliente preferente con descuento especial"
}
```

### Parámetros

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `order_id` | int | ✅ Sí | ID de la orden de venta (path) |
| `payment_terms` | string | ❌ No | Términos de pago (ej: "30 days", "Net 15") |
| `notes` | string | ❌ No | Notas adicionales para la factura |

### Requisitos

✅ La orden debe estar en estado **`confirmed`** o **`delivered`**  
✅ La orden **NO** debe tener ya una factura asociada  
✅ La orden debe tener **al menos un item**

### Response Exitoso (201 Created)

```json
{
  "invoice_id": "550e8400-e29b-41d4-a716-446655440000",
  "order_id": 123,
  "invoice_number": "A-2024-000456",
  "status": "created",
  "message": "Factura A-2024-000456 creada exitosamente desde orden 123"
}
```

### Errores Comunes

```json
// 400 - Orden no existe
{
  "detail": "Orden de venta 123 no encontrada"
}

// 400 - Orden en estado incorrecto
{
  "detail": "La orden debe estar confirmada o entregada (estado actual: draft)"
}

// 400 - Orden ya facturada
{
  "detail": "La orden 123 ya tiene factura: 550e8400-..."
}

// 400 - Sin items
{
  "detail": "La orden 123 no tiene items"
}
```

### Consultar Factura de una Orden

```http
GET /api/v1/tenant/sales_orders/{order_id}/invoice
```

**Response:**
```json
{
  "invoice_id": "550e8400-e29b-41d4-a716-446655440000",
  "invoice_number": "A-2024-000456",
  "order_id": 123,
  "created_at": "2024-01-15T10:30:00"
}
```

**404 si no tiene factura**

---

## 2️⃣ RECIBO POS → FACTURA FORMAL

### Caso de Uso
Cliente B2B compra en tienda física → Se genera recibo → Cliente solicita factura con datos fiscales

### Endpoint

```http
POST /api/v1/tenant/pos/receipts/{receipt_id}/invoice
Content-Type: application/json
Authorization: Bearer {token}

{
  "customer_id": "customer-uuid",
  "notes": "Factura solicitada por cliente empresarial"
}
```

### Parámetros

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `receipt_id` | UUID | ✅ Sí | ID del recibo POS (path) |
| `customer_id` | UUID | ✅ Sí | ID del cliente con datos fiscales |
| `notes` | string | ❌ No | Notas adicionales |

### Requisitos

✅ El recibo debe estar en estado **`paid`**  
✅ El recibo **NO** debe tener ya una factura asociada  
✅ El cliente debe **existir** y tener **datos fiscales completos** (identificación)

### Response Exitoso (201 Created)

```json
{
  "invoice_id": "660f9511-f3ac-52e5-b827-557766551111",
  "receipt_id": "770ea622-g4bd-63f6-c938-668877662222",
  "invoice_number": "A-2024-000457",
  "status": "created",
  "message": "Factura A-2024-000457 creada exitosamente desde recibo R-0123"
}
```

### Errores Comunes

```json
// 400 - UUID inválido
{
  "detail": "receipt_id o customer_id no son UUIDs válidos"
}

// 404 - Cliente no existe
{
  "detail": "Cliente customer-uuid no encontrado"
}

// 400 - Cliente sin datos fiscales
{
  "detail": "El cliente debe tener número de identificación fiscal"
}

// 400 - Recibo no existe
{
  "detail": "Recibo 770ea622-... no encontrado"
}

// 400 - Recibo ya facturado
{
  "detail": "El recibo ya tiene factura: 660f9511-..."
}

// 400 - Recibo no pagado
{
  "detail": "El recibo debe estar pagado (estado actual: draft)"
}
```

### Consultar Factura de un Recibo

```http
GET /api/v1/tenant/pos/receipts/{receipt_id}/invoice
```

**Response:**
```json
{
  "receipt_id": "770ea622-g4bd-63f6-c938-668877662222",
  "receipt_number": "R-0123",
  "invoice_id": "660f9511-f3ac-52e5-b827-557766551111",
  "invoice_number": "A-2024-000457",
  "created_at": "2024-01-15T14:30:00"
}
```

**404 si no tiene factura**

### Desvincular Factura (Solo Borradores)

```http
DELETE /api/v1/tenant/pos/receipts/{receipt_id}/invoice
```

⚠️ **ADVERTENCIA**: Solo para corrección de errores administrativos

**Requisitos:**
- Factura debe estar en estado **`draft`**
- No elimina la factura, solo rompe el vínculo

**Response:**
```json
{
  "status": "unlinked",
  "message": "Factura desvinculada exitosamente. El recibo vuelve a estado 'paid'."
}
```

**Errores:**
```json
// 403 - Factura ya emitida
{
  "detail": "No se puede desvincular una factura en estado 'emitida'. Solo facturas en borrador."
}
```

---

## 🔄 FLUJO COMPLETO DE DOCUMENTOS

### Flujo Normal de Venta B2B

```
1. Quote (Presupuesto)
        ↓ [futuro: POST /quotes/{id}/sales_order]
2. SalesOrder (draft)
        ↓ [POST /sales_orders - crear]
        ↓ [POST /sales_orders/{id}/confirm - confirmar]
3. SalesOrder (confirmed)
        ↓ [Logística entrega productos]
4. SalesOrder (delivered)
        ↓ [POST /sales_orders/{id}/invoice] ← NUEVO
5. Invoice (emitida)
        ↓ [POST /einvoicing/send - envío fiscal]
6. Invoice (enviada a SRI/SII)
        ↓ [Cliente paga]
7. Payment (conciliado)
```

### Flujo POS → Factura (Cliente B2B)

```
1. Cliente compra en tienda física
        ↓ [POST /pos/receipts - crear recibo]
2. POSReceipt (draft)
        ↓ [POST /pos/receipts/{id}/checkout - pagar]
3. POSReceipt (paid)
        ↓ [Cliente solicita factura con datos fiscales]
        ↓ [POST /pos/receipts/{id}/invoice] ← NUEVO
4. Invoice (emitida) + POSReceipt (invoiced)
        ↓ [POST /einvoicing/send - envío fiscal]
5. Invoice (enviada a SRI/SII)
```

---

## 🧪 EJEMPLOS DE USO

### Ejemplo 1: Crear Factura desde Orden de Venta

```bash
# 1. Crear orden de venta
curl -X POST "https://api.gestiqcloud.com/api/v1/tenant/sales_orders" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 456,
    "currency": "EUR",
    "items": [
      {
        "product_id": 789,
        "qty": 5,
        "unit_price": 25.00
      }
    ]
  }'

# Response: {"id": 123, "status": "draft", ...}

# 2. Confirmar orden
curl -X POST "https://api.gestiqcloud.com/api/v1/tenant/sales_orders/123/confirm" \
  -H "Authorization: Bearer {token}" \
  -d '{"warehouse_id": 1}'

# 3. Crear factura desde orden
curl -X POST "https://api.gestiqcloud.com/api/v1/tenant/sales_orders/123/invoice" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "payment_terms": "Net 30",
    "notes": "Pedido confirmado el 10/01/2024"
  }'

# Response:
# {
#   "invoice_id": "550e8400-...",
#   "invoice_number": "A-2024-000456",
#   "status": "created",
#   ...
# }
```

### Ejemplo 2: Crear Factura desde Recibo POS

```bash
# 1. Crear recibo POS (simplificado)
curl -X POST "https://api.gestiqcloud.com/api/v1/tenant/pos/receipts" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "shift_id": "shift-uuid",
    "register_id": "register-uuid",
    "lines": [
      {
        "product_id": "product-uuid",
        "qty": 2,
        "unit_price": 15.50,
        "tax_rate": 0.21
      }
    ]
  }'

# Response: {"id": "receipt-uuid", ...}

# 2. Procesar pago
curl -X POST "https://api.gestiqcloud.com/api/v1/tenant/pos/receipts/receipt-uuid/checkout" \
  -H "Authorization: Bearer {token}" \
  -d '{
    "payments": [
      {"method": "card", "amount": 37.47}
    ]
  }'

# 3. Cliente solicita factura formal
curl -X POST "https://api.gestiqcloud.com/api/v1/tenant/pos/receipts/receipt-uuid/invoice" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "customer-uuid",
    "notes": "Factura para empresa XYZ"
  }'

# Response:
# {
#   "invoice_id": "invoice-uuid",
#   "invoice_number": "A-2024-000457",
#   "status": "created",
#   ...
# }
```

---

## 📊 TRAZABILIDAD

Todos los documentos convertidos mantienen relaciones bidireccionales:

### Desde Factura → Origen

```sql
-- Ver de dónde vino una factura
SELECT 
  metadata::jsonb->>'sales_order_id' as from_sales_order,
  metadata::jsonb->>'pos_receipt_id' as from_pos_receipt
FROM invoices 
WHERE id = 'invoice-uuid';
```

### Desde Orden → Factura

```sql
-- Ver factura de una orden
SELECT i.* 
FROM invoices i
WHERE i.metadata::jsonb->>'sales_order_id' = '123';
```

### Desde Recibo POS → Factura

```sql
-- Ver factura de un recibo
SELECT i.*
FROM pos_receipts r
JOIN invoices i ON i.id = r.invoice_id
WHERE r.id = 'receipt-uuid';
```

---

## ⚙️ CONFIGURACIÓN REQUERIDA

### Función SQL de Numeración

Los endpoints requieren la función SQL `assign_next_number`:

```sql
CREATE OR REPLACE FUNCTION public.assign_next_number(
    tenant uuid,
    tipo text,
    anio int,
    serie text
) RETURNS text AS $$
DECLARE
    next_num int;
BEGIN
    -- Implementación atómica de numeración
    -- Ver: apps/backend/app/modules/shared/services/numbering.py
    ...
END;
$$ LANGUAGE plpgsql;
```

Si no existe, el sistema usa fallback (no recomendado para producción).

---

## 🧹 LIMPIEZA Y MANTENIMIENTO

### Reportes de Conversiones

```sql
-- Órdenes facturadas hoy
SELECT 
    so.id as order_id,
    i.numero as invoice_number,
    i.total,
    i.fecha_creacion
FROM sales_orders so
JOIN invoices i ON i.metadata::jsonb->>'sales_order_id' = so.id::text
WHERE DATE(i.fecha_creacion) = CURRENT_DATE;

-- Recibos POS convertidos a factura
SELECT 
    r.number as receipt_number,
    i.numero as invoice_number,
    i.total,
    i.fecha_creacion
FROM pos_receipts r
JOIN invoices i ON i.id = r.invoice_id
WHERE DATE(i.fecha_creacion) >= CURRENT_DATE - INTERVAL '7 days';
```

---

## 📚 REFERENCIAS

- [DocumentConverter Service](file:///c:/Users/pc_cashabamba/Documents/GitHub/proyecto/apps/backend/app/modules/shared/services/document_converter.py)
- [Numbering Service](file:///c:/Users/pc_cashabamba/Documents/GitHub/proyecto/apps/backend/app/modules/shared/services/numbering.py)
- [Sales Conversions Router](file:///c:/Users/pc_cashabamba/Documents/GitHub/proyecto/apps/backend/app/modules/ventas/interface/http/conversions.py)
- [POS Conversions Router](file:///c:/Users/pc_cashabamba/Documents/GitHub/proyecto/apps/backend/app/modules/pos/interface/http/conversions.py)

---

**Versión**: 1.0  
**Última actualización**: 2024-11-06  
**Autor**: GestiqCloud Development Team
