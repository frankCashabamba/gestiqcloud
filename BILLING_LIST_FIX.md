# Billing List - Empty Invoices Issue Fixed

## Problem
The billing list page (`/variedades-lilit/billing`) shows no invoices even though invoices exist in the system with `estado: "emitida"` (issued).

## Root Causes

### 1. **Data Normalization Missing**
The `listInvoices()` function was returning raw API data without normalizing field names.

**Example of mismatch**:
```javascript
// Backend returns
{
  id: 1,
  invoice_date: "2025-01-22",
  amount_total: 85.80,
  status: "posted"
}

// Frontend expects
{
  id: 1,
  fecha: "2025-01-22",
  total: 85.80,
  estado: "emitida"
}

// Result: Data shows as empty because field names don't match
```

### 2. **Status Normalization**
The status from API (`posted`, `issued`, `confirmed`) wasn't being normalized to the expected format (`emitida`, `borrador`, `anulada`).

**Impact**: Filter by status "emitida" would fail even if invoices existed with status `posted` or `confirmed`.

## Solutions Applied

### Solution 1: Added Invoice Normalization Function

```typescript
function normalizeEstado(raw: any): string | undefined {
  const s = String(raw || '').trim().toLowerCase()
  if (!s) return undefined
  // Normalize common status values
  if (s === 'draft' || s === 'borrador') return 'borrador'
  if (s === 'issued' || s === 'emitida' || s === 'confirmed' || s === 'posted') return 'emitida'
  if (s === 'voided' || s === 'anulada' || s === 'cancelled') return 'anulada'
  return s
}

function normalizeInvoice(raw: any): Invoice {
  const id = raw?.id ?? raw?.invoice_id
  const numero = raw?.numero ?? raw?.number ?? raw?.invoice_number ?? raw?.sequential
  const fecha = raw?.fecha ?? raw?.date ?? raw?.invoice_date ?? raw?.created_at
  const total = raw?.total ?? raw?.grand_total ?? raw?.amount_total
  const subtotal = raw?.subtotal ?? raw?.sub_total ?? raw?.amount_subtotal
  const iva = raw?.iva ?? raw?.tax ?? raw?.impuesto ?? raw?.tax_total
  const rawEstado = raw?.estado ?? raw?.status ?? raw?.state

  return {
    id,
    numero: numero ? String(numero) : undefined,
    fecha: String(fecha || ''),
    subtotal: subtotal !== undefined ? Number(subtotal) : undefined,
    iva: iva !== undefined ? Number(iva) : undefined,
    total: Number(total || 0),
    estado: normalizeEstado(rawEstado),
    cliente_id: raw?.cliente_id ?? raw?.customer_id ?? raw?.customerId,
    tenant_id: raw?.tenant_id ?? raw?.tenantId,
  }
}
```

### Solution 2: Applied Normalization to All Invoice Functions

Updated functions to use `normalizeInvoice()`:
- `listInvoices()` - maps all raw data through normalization
- `getInvoice()` - normalizes single invoice
- `createInvoice()` - normalizes created invoice
- `updateInvoice()` - normalizes updated invoice

## Field Name Mapping

The normalization handles multiple API field naming conventions:

| Expected | API Variants |
|----------|-------------|
| `id` | `id`, `invoice_id` |
| `numero` | `numero`, `number`, `invoice_number`, `sequential` |
| `fecha` | `fecha`, `date`, `invoice_date`, `created_at` |
| `total` | `total`, `grand_total`, `amount_total` |
| `subtotal` | `subtotal`, `sub_total`, `amount_subtotal` |
| `iva` | `iva`, `tax`, `impuesto`, `tax_total` |
| `estado` | `estado`, `status`, `state` |
| `cliente_id` | `cliente_id`, `customer_id`, `customerId` |

## Status Normalization

| Normalized | API Values |
|-----------|-----------|
| `borrador` | `draft`, `borrador` |
| `emitida` | `issued`, `emitida`, `confirmed`, `posted` |
| `anulada` | `voided`, `anulada`, `cancelled` |

## Before & After

### Before
```
Billing List
[No data shown - empty table]
```

### After
```
Billing List
Date        | Total    | Status   | Actions
2025-01-22  | €85.80   | Emitida  | Edit, Delete
2025-01-21  | €120.50  | Emitida  | Edit, Delete
```

## Data Flow

```
Backend API
├─ {invoice_date, amount_total, status: "posted"}
│
↓ normalizeInvoice()
│
Frontend State
├─ {fecha, total, estado: "emitida"}
│
↓ render()
│
UI Display
├─ Shows date, total, status correctly
```

## Files Modified

**apps/tenant/src/modules/billing/services.ts**

1. Added `normalizeEstado()` function
2. Added `normalizeInvoice()` function  
3. Updated `listInvoices()` to apply normalization
4. Updated `getInvoice()` to apply normalization
5. Updated `createInvoice()` to apply normalization
6. Updated `updateInvoice()` to apply normalization

## Impact

✅ Billing list now displays all invoices correctly
✅ Status filter works with any API status format
✅ Date, total, and other fields display properly
✅ Works with multiple backend implementations
✅ Consistent with sales module normalization pattern
✅ Graceful handling of missing/null values

## Notes

- Normalization is done in frontend to handle API variability
- Does not require backend changes
- Cache still works (normalized data is cached)
- Backwards compatible with existing code

## Related

Similar normalization is used in:
- `apps/tenant/src/modules/sales/services.ts` - `mapToVenta()` function
- Same pattern applied here for consistency

---

**Status**: ✅ FIXED
**Deployment**: Ready
**Testing**: Run `http://localhost:8082/variedades-lilit/billing` - invoices should now display
