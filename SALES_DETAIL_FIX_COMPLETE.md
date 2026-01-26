# Sales Detail View - Fixed

## Problems Identified

1. **Empty data in detail view** - Numbers, dates, customer info all showed empty
2. **Raw text instead of translations** - UI showing hardcoded English text
3. **Data mapping inconsistency** - `getVenta()` not applying same normalization as `listVentas()`

## Root Causes

### Problem 1: Empty Data in Detail View
**File**: `apps/tenant/src/modules/sales/services.ts`

The `getVenta()` function was returning raw API response without normalizing field names.

**Example**:
- Backend returns: `{ order_date: "2025-01-22", grand_total: 85.80 }`
- Frontend expected: `{ fecha: "2025-01-22", total: 85.80 }`
- Result: All fields were undefined/empty

### Problem 2: Hardcoded English Text
**File**: `apps/tenant/src/modules/sales/Detail.tsx`

Component had hardcoded English strings like "Loading...", "Edit", "Delete", "Print", etc.

### Problem 3: Missing Translation Keys
Several keys were not defined in translation files, causing keys to display literally.

## Fixes Applied

### Fix 1: Data Normalization in services.ts

```typescript
// Before: Raw data returned as-is
export async function getVenta(id: number | string): Promise<Venta> {
    const { data } = await tenantApi.get<Venta>(TENANT_SALES.byId(id))
    return data  // ❌ Missing normalization
}

// After: Apply mapToVenta normalization
export async function getVenta(id: number | string): Promise<Venta> {
    const { data } = await tenantApi.get<any>(TENANT_SALES.byId(id))
    return mapToVenta(data)  // ✅ Normalizes field names
}
```

Applied same fix to:
- `createVenta()`
- `updateVenta()`

**Normalization handles**:
- `order_date` / `fecha` → `fecha`
- `grand_total` / `total` → `total`
- `customer_name` / `client_name` → `cliente_nombre`
- Status normalization: `draft` → `borrador`, `confirmed` → `emitida`

### Fix 2: Internationalization in Detail.tsx

**Changes**:
- Added `useTranslation()` hook
- Replaced all hardcoded strings with `t()` function calls
- Used existing translation keys from `en.json` and `es.json`

**Examples**:
```tsx
// Before
<h3 className="...">General information</h3>
<label>Number:</label>
<button>Edit</button>

// After
<h3>{t('sales.title')} {t('common.info')}</h3>
<label>{t('sales.saleNumber')}:</label>
<button>{t('common.edit')}</button>
```

### Fix 3: Added Missing Translation Keys

**Added to en.json and es.json**:

**Common keys**:
- `view` - "View" / "Ver"
- `print` - "Print" / "Imprimir"  
- `close` - "Close" / "Cerrar"
- `open` - "Open" / "Abrir"
- `add` - "Add" / "Agregar"
- `remove` - "Remove" / "Quitar"
- `update` - "Update" / "Actualizar"
- `refresh` - "Refresh" / "Actualizar"
- `sort` - "Sort" / "Ordenar"
- `download` - "Download" / "Descargar"
- `upload` - "Upload" / "Cargar"
- `info` - "Information" / "Información"

**Sales keys**:
- `exportCsv` - "Export CSV" / "Exportar CSV"
- `searchPlaceholder` - "Search sales..." / "Buscar ventas..."
- `invoice` - "Invoice" / "Facturar"

**Billing keys**:
- `fields.notes` - "Notes" / "Notas"

## Files Modified

1. **apps/tenant/src/modules/sales/services.ts**
   - Updated: `getVenta()`, `createVenta()`, `updateVenta()`
   - Change: Applied `mapToVenta()` normalization to all functions

2. **apps/tenant/src/modules/sales/Detail.tsx**
   - Added: `useTranslation()` hook
   - Replaced: All hardcoded strings with i18n keys
   - Updated: All section headings and button labels

3. **apps/tenant/src/i18n/locales/en.json**
   - Added: 15+ new translation keys

4. **apps/tenant/src/i18n/locales/es.json**
   - Added: 15+ new translation keys (Spanish equivalents)

## Before & After

### Before
```
Sale Detail
Number: -          (empty)
Date:              (empty)
Customer: ID: undefined
Subtotal: $0.00
```

### After
```
Sale Detail  
Number: SALE-001
Date: 2025-01-22
Customer: John Doe
Subtotal: $85.80
```

And respects tenant language:
- English UI if company `locale: "en"`
- Spanish UI if company `locale: "es"`

## Data Flow

```
Backend API Response
├─ order_date: "2025-01-22"
├─ grand_total: 85.80
├─ customer_name: "John"
└─ status: "confirmed"
    ↓ mapToVenta()
Frontend Venta Object
├─ fecha: "2025-01-22" ✓
├─ total: 85.80 ✓
├─ cliente_nombre: "John" ✓
└─ estado: "emitida" ✓
    ↓ render()
UI Display
├─ Date: 2025-01-22
├─ Subtotal: $85.80
├─ Customer: John
└─ Status: Emitida
```

## Testing

✅ Detail view loads data correctly
✅ All fields display proper values
✅ Language respects tenant configuration
✅ Create/Update operations work with normalization
✅ No hardcoded English text in UI
✅ All buttons show correct translations

## Related Pages Fixed

The same services are used by:
- Sales List (`modules/sales/List.tsx`) ✓
- Sales Edit (`modules/sales/Form.tsx`) - will inherit fix
- Sales Create - will inherit fix
- Any other component using `getVenta()` ✓

## Notes

- `mapToVenta()` is smart about field name variations
- Handles multiple naming conventions from different backends
- Normalizes dates and numbers safely
- Falls back gracefully for missing fields

---

**Status**: ✅ COMPLETE AND VERIFIED
**Impact**: Affects all sales operations
**Breaking Changes**: None (internal normalization)
**Deployment**: Ready
