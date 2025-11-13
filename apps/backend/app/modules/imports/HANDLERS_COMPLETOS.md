# Handlers Completos - Implementación 100%

## ✅ Estado: IMPLEMENTACIÓN REAL Y COMPLETA

Todos los handlers están implementados con **inserción real en base de datos**. Sin skeletons, sin IDs ficticios.

---

## 📊 Handlers Implementados

### 1. **InvoiceHandler** ✅ 100%

**Tabla destino**: `invoices` + `invoice_lines`

**Funcionalidad**:
- Crea facturas reales con todas las líneas
- Busca/crea proveedor automáticamente en tabla `clients`
- Extrae datos de múltiples formatos (PDF OCR, XML, Excel)
- Soporta múltiples alias de campos
- Maneja fechas en varios formatos (ISO, DD/MM/YYYY, etc.)
- Calcula subtotales, IVA y total automáticamente

**Campos soportados**:
```python
{
    "invoice_number": "numero de factura",
    "invoice_date": "fecha de emisión",
    "vendor_name": "nombre del proveedor",
    "subtotal": "base imponible",
    "tax": "iva/impuesto",
    "total": "importe total",
    "lines": [  # opcional
        {
            "descripcion": "producto/servicio",
            "cantidad": 1,
            "precio_unitario": 100.00,
            "iva": 12.00
        }
    ]
}
```

**Archivos compatibles**:
- PDF: `Invoice-B7322538-0003.pdf`
- XML: `2024-001.xml` (Facturae/SRI)
- Excel/CSV: con columnas de factura

---

### 2. **BankHandler** ✅ 100%

**Tabla destino**: `bank_transactions` + `bank_accounts`

**Funcionalidad**:
- Crea transacciones bancarias reales
- Busca/crea cuenta bancaria automáticamente
- Soporta múltiples formatos: CSV, MT940, CAMT.053, Excel
- Detecta dirección (débito/crédito) automáticamente
- Categoriza movimientos por keywords
- Maneja múltiples monedas (EUR, USD)

**Campos soportados**:
```python
{
    "date": "fecha del movimiento",
    "amount": "importe (positivo o negativo)",
    "direction": "debit o credit",
    "description": "concepto/narrativa",
    "reference": "referencia bancaria",
    "iban": "IBAN cuenta (opcional)",
    "currency": "EUR, USD, etc.",
    "counterparty_name": "contrapartida",
    "tipo": "transferencia, tarjeta, etc."
}
```

**Archivos compatibles**:
- Excel: `movimientos.xlsx`
- CSV: con columnas bancarias
- MT940: formato SWIFT
- CAMT.053: formato ISO 20022 XML

**Tipos de movimiento**:
- Transferencia
- Tarjeta
- Efectivo
- Recibo/Domiciliación
- Otro

---

### 3. **ExpenseHandler** ✅ 100%

**Tabla destino**: `gastos`

**Funcionalidad**:
- Crea gastos/recibos reales
- Busca proveedor existente opcionalmente
- Soporta categorización automática
- Maneja formas de pago múltiples
- Calcula importes e IVA correctamente

**Campos soportados**:
```python
{
    "date": "fecha del gasto",
    "description": "concepto",
    "category": "categoria del gasto",
    "amount": "importe total",
    "tax": "iva",
    "payment_method": "efectivo, tarjeta, transferencia",
    "invoice_number": "numero de factura (opcional)",
    "vendor": "proveedor (opcional)"
}
```

**Archivos compatibles**:
- PDF: `Receipt-2921-4611.pdf`, `recibos.pdf`
- Imágenes JPG/PNG de tickets
- Excel/CSV: con columnas de gastos

**Categorías soportadas**:
- nomina
- alquiler
- suministros
- marketing
- servicios
- otros

---

### 4. **ProductHandler** ✅ 100%

**Tabla destino**: `products` + `product_categories` + `stock_items` + `warehouses`

**Funcionalidad**:
- Crea/actualiza productos con stock
- Crea categorías automáticamente si no existen
- Genera SKU automático si falta
- Inicializa stock en almacén
- Crea almacenes si no existen
- Activa productos automáticamente (opcional)

**Campos soportados**:
```python
{
    "name": "nombre del producto",
    "price": "precio venta",
    "stock": "cantidad inicial",
    "category": "categoria",
    "sku": "código (auto si falta)",
    "unit": "unidad medida"
}
```

**Archivos compatibles**:
- Excel: `Stock-02-11-2025.xlsx`, `67 Y 68 CATALOGO.xlsx`
- CSV: con columnas de productos

---

## 🔧 Uso desde el Frontend

### Flujo completo:

```typescript
// 1. Usuario sube archivo
uploadFile(file)

// 2. Se detecta tipo automático
detectarTipoDocumento(headers) → 'productos' | 'invoices' | 'bank' | 'receipts'

// 3. Se crea batch y se procesan datos
createBatch({ source_type: tipo })
ingestBatch(batchId, { rows: datos })

// 4. Vista previa y validación
navigate(`/importador/preview?batch_id=${batchId}`)

// 5. Usuario revisa/modifica
patchItem(batchId, itemId, { field, value })

// 6. Promoción a tabla final
promoteBatch(batchId, { auto: true })
```

### Respuesta de promote:

```json
{
  "created": 45,    // Items creados en tabla destino
  "skipped": 2,     // Items ya existentes (idempotente)
  "failed": 1       // Items con error
}
```

---

## 🎯 Archivos de `importacion/` Soportados

| Archivo | Tipo Detectado | Handler | Tabla Destino |
|---------|----------------|---------|---------------|
| `Stock-02-11-2025.xlsx` | productos | ProductHandler | products |
| `67 Y 68 CATALOGO.xlsx` | productos | ProductHandler | products |
| `19-01-24..xlsx` | genérico | *depende contenido* | - |
| `movimientos.xlsx` | bank | BankHandler | bank_transactions |
| `Invoice-B7322538-0003.pdf` | invoices | InvoiceHandler | invoices |
| `2024-001.xml` | invoices | InvoiceHandler | invoices |
| `Receipt-2921-4611.pdf` | receipts | ExpenseHandler | gastos |
| `ReciboPDF_037640_003368.pdf` | receipts | ExpenseHandler | gastos |
| `recibos.pdf` | receipts | ExpenseHandler | gastos |
| `Septiembre.pdf` | genérico | *OCR analiza* | - |
| `tiken2.pdf` | receipts | ExpenseHandler | gastos |
| `tikent.pdf` | receipts | ExpenseHandler | gastos |

---

## 🔒 Seguridad y Validación

### Idempotencia:
- Cada item tiene `dedupe_hash` único
- La promoción verifica si ya existe antes de insertar
- Items duplicados se marcan como `SKIPPED`

### Tenant Isolation:
- Todos los handlers verifican `tenant_id`
- RLS (Row Level Security) activo en todas las tablas
- Imposible acceder a datos de otro tenant

### Validación antes de promote:
- Campos requeridos verificados
- Formatos de fecha validados
- Importes numéricos validados
- Categorías/proveedores verificados

---

## 📝 Ejemplos de Datos Normalizados

### Factura (de PDF Invoice-B7322538-0003.pdf):
```json
{
  "doc_type": "invoice",
  "invoice_number": "B7322538-0003",
  "vendor_name": "ACME Corp",
  "invoice_date": "2024-11-01",
  "subtotal": 100.00,
  "tax": 12.00,
  "total": 112.00,
  "lines": [
    {
      "descripcion": "Servicio de consultoría",
      "cantidad": 1,
      "precio_unitario": 100.00,
      "iva": 12.00
    }
  ]
}
```

### Movimiento bancario (de movimientos.xlsx):
```json
{
  "doc_type": "bank_tx",
  "date": "2024-11-15",
  "amount": 1500.00,
  "direction": "credit",
  "description": "Transferencia recibida - Cliente ABC",
  "reference": "TRX-20241115-001",
  "currency": "USD",
  "tipo": "transferencia"
}
```

### Gasto (de Receipt-2921-4611.pdf):
```json
{
  "doc_type": "expense",
  "date": "2024-11-10",
  "description": "Combustible",
  "category": "suministros",
  "amount": 45.50,
  "tax": 5.46,
  "total": 50.96,
  "payment_method": "tarjeta",
  "vendor": "Gasolinera Shell"
}
```

### Producto (de Stock-02-11-2025.xlsx):
```json
{
  "doc_type": "product",
  "name": "Pan Integral 500g",
  "price": 2.50,
  "stock": 150,
  "category": "PANADERIA",
  "sku": "PAN-0023",
  "unit": "unidad"
}
```

---

## ✅ Checklist de Implementación

- [x] InvoiceHandler → Inserción real en `invoices` + `invoice_lines`
- [x] BankHandler → Inserción real en `bank_transactions` + `bank_accounts`
- [x] ExpenseHandler → Inserción real en `gastos`
- [x] ProductHandler → Inserción real en `products` + stock (ya existía)
- [x] Actualizado `use_cases.py` para usar firmas correctas
- [x] Idempotencia en todos los handlers
- [x] Manejo de errores con try/catch
- [x] Soporte múltiples alias de campos
- [x] Soporte múltiples formatos de fecha
- [x] Creación automática de entidades relacionadas (clientes, cuentas, categorías)
- [x] Tenant isolation con UUID
- [x] Sin código hackeado ni IDs ficticios

---

## 🚀 Próximos Pasos Opcionales

1. **Conciliación bancaria**: Match automático de facturas con movimientos
2. **OCR mejorado**: Mejor extracción de campos de PDFs complejos
3. **Validación SRI**: Verificar firmas digitales en XMLs Ecuador
4. **Webhooks**: Notificaciones al completar imports
5. **Dashboards**: Métricas de importaciones por tipo

---

**Versión**: 1.0 - Implementación completa  
**Fecha**: 2025-11-05  
**Autor**: Sistema de importación GestiqCloud
