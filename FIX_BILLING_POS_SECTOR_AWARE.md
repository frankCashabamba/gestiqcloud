# Billing POS Sector-Aware Fix

## Problem
After loading invoice data with `joinedload()`, the API returned a validation error because:
- Invoices in a retail tenant contained `POSLine` items (sector = 'pos')
- The Pydantic schema only accepted `bakery` and `workshop` line types
- The discriminated union was too strict for multi-sector data

## Root Cause
The invoicing schema was designed to support only `bakery` and `workshop` sectors, but:
1. POS receipts create invoices with `POSLine` items (sector = 'pos')
2. When a tenant is retail, facturas are created from POS with these line types
3. The schema validation rejected 'pos' as an invalid discriminator value

## Solution

### Backend Changes

#### 1. **schemas.py** - Added POSLine Support
```python
class POSLine(LineaBase):
    """Generic POS line item."""
    sector: Literal["pos"]

class POSLineOut(POSLine):
    """POS line output schema."""
    model_config = ConfigDict(from_attributes=True)

# Updated union to accept all line types
LineaFacturaOut = Annotated[
    BakeryLineOut | WorkshopLineOut | POSLineOut, 
    Field(discriminator="sector")
]
```

#### 2. **crud.py** - Added Sector Awareness
- Imported `Tenant` model and `POSLine` model
- Added `_get_sector_template()` helper to get tenant's configured sector
- Sets foundation for future sector-based filtering

#### 3. **tenant.py (endpoints)** - Enhanced Data Loading
- All endpoints now use `joinedload(Invoice.lines)` and `joinedload(Invoice.customer)`
- GET, PUT, and POST endpoints properly reload relationships after mutations
- Ensures complete data available for Pydantic validation

### Frontend Changes

#### 1. **services.ts** - Enhanced Line Normalization
- Added comment explaining POS line handling
- Normalizer converts all line types to generic `InvoiceLine` format
- Handles both sector-specific fields and generic POS fields
- No special UI logic needed for POS lines - they render as generic invoice lines

## Data Flow - Sector-Aware Invoicing

```
Tenant Created (retail sector)
    ↓
POS Receipt Generated → Creates Invoice with POSLine items
    ↓
GET /api/v1/tenant/invoicing/{id}
    ├─ Loads Invoice with joinedload(lines)
    ├─ Lines include POSLine objects (sector='pos')
    └─ Schema validates all line types (bakery, workshop, pos)
    ↓
API Response includes lines: [{sector: 'pos', description: '...'}]
    ↓
Frontend normalizeInvoice()
    ├─ Extracts all line items regardless of sector
    └─ Normalizes to generic InvoiceLine format
    ↓
Form displays products correctly for editing

```

## Key Points

- **Backwards Compatible**: Existing bakery and workshop invoices unaffected
- **Sector-Agnostic Rendering**: Frontend treats all line types identically
- **Future-Proof**: Can add new sector types (e.g., 'restaurant', 'pharmacy') by adding new schema classes
- **Multilingual**: Form labels still use i18n (no hardcoded text)

## Testing

1. Create a retail tenant
2. Generate POS receipts (creates invoices with POSLine items)
3. Navigate to billing list - should load without validation errors
4. Click "Editar" on a POS invoice - products should display in form
5. Edit products, save, and verify updates work

## Affected Endpoints

- `GET /api/v1/tenant/invoicing` - List invoices
- `GET /api/v1/tenant/invoicing/{id}` - Get single invoice
- `PUT /api/v1/tenant/invoicing/{id}` - Update invoice
- `POST /api/v1/tenant/invoicing/{id}/emitir` - Emit invoice

All now properly load and validate invoices from any sector (retail, bakery, workshop, etc.).
