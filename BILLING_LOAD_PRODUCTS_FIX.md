# Billing Products Loading Fix

## Problem
When editing an invoice at `http://localhost:8082/variedades-lilit/billing/{id}/editar`, the form was not loading the products (lineas) that were previously sold, even though:
- The list view showed all invoices with correct data
- The backend had the data
- The API schema included `lineas` field

## Root Cause
The issue was caused by **lazy loading of ORM relationships**:

1. **Backend (SQLAlchemy ORM)**: The GET endpoints were not using `joinedload()` to eagerly load the `Invoice.lines` relationship
2. **Pydantic Schema**: Missing `lines` field alias for JSON serialization
3. **Frontend**: The `normalizeInvoice()` function wasn't extracting and mapping the `lineas` field

## Changes Made

### Backend (apps/backend/app/modules/invoicing/)

#### 1. **interface/http/tenant.py**
- **GET /{factura_id}**: Added `joinedload()` for `lines` and `customer` relationships
- **PUT /{factura_id}**: Added `joinedload()` for relationships + refresh with relation attributes
- **POST /{factura_id}/emitir**: Reload invoice with relations after emission

#### 2. **schemas.py**
- Added `lines: list[LineaFacturaOut] = []` field as alias for ORM relationship
- Pydantic now correctly maps both `lineas` (Spanish) and `lines` (English) field names

#### 3. **crud.py**
- `create_with_lineas()`: Changed `db.refresh(factura)` to `db.refresh(factura, ["lines", "customer"])` to reload relationships

### Frontend (apps/tenant/src/modules/billing/)

#### 1. **services.ts**
- Updated `Invoice` interface to include:
  - `cliente_nombre?: string`
  - `descripcion?: string`
  - `lineas?: InvoiceLine[]`

- Enhanced `normalizeInvoice()` function to:
  - Extract `lineas` from API response (handles both `lineas`, `lines`, `invoice_lines` field names)
  - Normalize line items with proper field mapping (Spanish/English variants)
  - Calculate totals for each line item
  - Map `cliente_nombre` and `descripcion` fields

## Data Flow

```
Backend API Response (Invoice with lines)
    ↓
normalizeInvoice() processing
    ↓
Invoice interface with populated lineas[]
    ↓
Form component receives data in useEffect
    ↓
form.lineas populated in state
    ↓
Lines table renders with all products
```

## Testing

1. Navigate to billing list
2. Click "Editar" (Edit) on any invoice
3. Verify that all product lines are now displayed in the lines table
4. Verify product data (description, quantity, unit price, total) is correct
5. Ability to add/remove/modify lines should work as expected

## Translation Status
- All field labels use i18n keys (billing.sectorInvoice.*)
- No hardcoded Spanish/English text in form
- Error messages use translation keys from `common.` and `billing.` namespaces

## Related Files
- `/apps/backend/app/models/core/facturacion.py` - Invoice ORM model
- `/apps/backend/app/models/core/invoiceLine.py` - InvoiceLine ORM model
- `/apps/tenant/src/modules/billing/Form.tsx` - Form component using service
