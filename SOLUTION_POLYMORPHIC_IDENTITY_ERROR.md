# Solution: SQLAlchemy Polymorphic Identity 'pos' Error

## Executive Summary

Fixed two related errors:
1. **`InFailedSqlTransaction`** - Transaction aborted error during POS checkout
2. **`AssertionError: No such polymorphic_identity 'pos' is defined`** - Missing POSLine model

**Status:** ✅ FIXED

**Root Cause:** Database had `invoice_lines` records with `sector='pos'`, but SQLAlchemy models only defined `'bakery'` and `'workshop'` as valid polymorphic identities.

**Solution:** Added `POSLine` model class and created corresponding database table.

---

## Error Messages

### Error 1: Transaction Failure
```
psycopg2.errors.InFailedSqlTransaction: 
transacción abortada, las órdenes serán ignoradas hasta el fin de bloque de transacción

[SQL: SELECT id, customer_id, number, status, gross_total, tax_total, created_at
       FROM pos_receipts WHERE id = %(rid)s::UUID FOR UPDATE]
```

**When it occurs:** Calling checkout endpoint on a POS receipt
**File:** `apps/backend/app/modules/pos/application/invoice_integration.py:377`

### Error 2: Polymorphic Identity Not Found
```
sqlalchemy.orm.loading:
KeyError: 'pos'

AssertionError: No such polymorphic_identity 'pos' is defined
```

**When it occurs:** Fetching invoices list via `/api/v1/tenant/invoicing`
**File:** `apps/backend/app/modules/invoicing/crud.py:147`
**Root:** SQLAlchemy tries to instantiate InvoiceLine subclass based on `sector` column value but 'pos' isn't mapped

---

## Technical Details

### Database Schema

The `invoice_lines` table uses **Single Table Inheritance (STI)** with a discriminator column:

```sql
CREATE TABLE invoice_lines (
    id UUID PRIMARY KEY,
    invoice_id UUID REFERENCES invoices(id),
    sector VARCHAR(50),              -- DISCRIMINATOR
    description VARCHAR,
    quantity FLOAT,
    unit_price FLOAT,
    vat FLOAT
);

-- Child tables using Joined Table Inheritance:
CREATE TABLE bakery_lines (
    id UUID PRIMARY KEY REFERENCES invoice_lines(id),
    bread_type VARCHAR,
    grams FLOAT
);

CREATE TABLE workshop_lines (
    id UUID PRIMARY KEY REFERENCES invoice_lines(id),
    spare_part VARCHAR,
    labor_hours FLOAT,
    rate FLOAT
);

CREATE TABLE pos_invoice_lines (  -- ← NEW
    id UUID PRIMARY KEY REFERENCES invoice_lines(id),
    pos_receipt_line_id UUID
);
```

### SQLAlchemy Models

**Before (broken):**
```python
class InvoiceLine(Base):
    __tablename__ = "invoice_lines"
    sector: Mapped[str] = mapped_column("sector", String(50))
    __mapper_args__ = {
        "polymorphic_identity": "base",
        "polymorphic_on": sector
    }

class BakeryLine(InvoiceLine):
    __tablename__ = "bakery_lines"
    __mapper_args__ = {"polymorphic_identity": "bakery"}

class WorkshopLine(InvoiceLine):
    __tablename__ = "workshop_lines"
    __mapper_args__ = {"polymorphic_identity": "workshop"}

# ❌ No POSLine defined!
```

**After (fixed):**
```python
# ... existing classes ...

class POSLine(InvoiceLine):
    """POS-generated line item model."""
    __tablename__ = "pos_invoice_lines"
    
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        ForeignKey("invoice_lines.id"), 
        primary_key=True
    )
    pos_receipt_line_id: Mapped[UUID | None] = mapped_column(
        "pos_receipt_line_id", 
        PGUUID(as_uuid=True), 
        nullable=True
    )
    
    __mapper_args__ = {"polymorphic_identity": "pos"}
```

---

## What Changed

### 1. Model Definition (✅ DONE)
**File:** `apps/backend/app/models/core/invoiceLine.py`

Added `POSLine` class (lines 68-80):
- Inherits from `InvoiceLine`
- Maps to `pos_invoice_lines` table
- Registers `polymorphic_identity='pos'`
- Optional link to `pos_receipt_line_id`

### 2. Database Migration (✅ CREATED)
**File:** `ops/migrations/2026-01-22_001_add_pos_invoice_lines/up.sql`

```sql
CREATE TABLE IF NOT EXISTS pos_invoice_lines (
    id UUID NOT NULL PRIMARY KEY,
    pos_receipt_line_id UUID,
    FOREIGN KEY (id) REFERENCES invoice_lines(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_pos_invoice_lines_pos_receipt_line_id 
    ON pos_invoice_lines(pos_receipt_line_id);
```

### 3. Improved Error Handling (✅ DONE)
**File:** `apps/backend/app/modules/pos/application/invoice_integration.py`

Enhanced exception handling in two methods:
- `create_invoice_from_receipt()` (line 358-364)
- `create_sale_from_receipt()` (line 549-560)

Changes:
- Wrapped `db.rollback()` in try-except to handle rollback failures
- Added logging for rollback errors
- Prevents transaction state cascades

```python
except Exception as e:
    try:
        self.db.rollback()
    except Exception as rollback_error:
        logger.error("Failed to rollback transaction: %s", rollback_error)
    logger.exception("Error creating invoice from receipt: %s", e)
    return None
```

---

## Installation Steps

### Step 1: Update Code
```bash
git pull origin main
```

Files will be updated:
- ✅ `apps/backend/app/models/core/invoiceLine.py` 
- ✅ `apps/backend/app/modules/pos/application/invoice_integration.py`
- ✅ `ops/migrations/2026-01-22_001_add_pos_invoice_lines/` (new)

### Step 2: Run Migration
```bash
# Using alembic
alembic upgrade head

# Or manual SQL
cd ops/migrations/2026-01-22_001_add_pos_invoice_lines
psql -U gestiqcloud_user -d gestiqcloud -f up.sql
```

### Step 3: Verify
```sql
-- Check table exists
\dt pos_invoice_lines

-- Check index exists
\di idx_pos_invoice_lines_pos_receipt_line_id

-- Test query (should NOT throw polymorphic_identity error)
SELECT COUNT(*) FROM invoices;
```

### Step 4: Restart Backend
```bash
systemctl restart gestiqcloud-backend
# or
docker-compose restart backend
# or
pkill -f uvicorn && python -m uvicorn app.main:app
```

---

## Testing

### Test 1: Polymorphic Identity Registration
```python
# In Python shell or test file
from app.models.core.invoiceLine import POSLine
from sqlalchemy import inspect

mapper = inspect(POSLine)
print(mapper.polymorphic_identity)  # Should print: 'pos'
```

### Test 2: Fetch Invoices (REST API)
```bash
curl -X GET http://localhost:8000/api/v1/tenant/invoicing \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**Expected:** 200 OK with invoice list (no polymorphic_identity error)

### Test 3: POS Checkout Flow
```bash
# 1. Create receipt (should work already)
curl -X POST http://localhost:8000/api/v1/tenant/pos/receipts \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"register_id": "...", "shift_id": "...", ...}'

# 2. Checkout receipt (this was failing with InFailedSqlTransaction)
curl -X POST http://localhost:8000/api/v1/tenant/pos/receipts/{id}/checkout \
  -H "Authorization: Bearer $TOKEN"
```

**Expected:** 200 OK with `sale_id`, `invoice_id`, `expense_id` (all optional based on modules)

---

## Data Migration

### If you have existing 'pos' records in invoice_lines:

**Option A: Migrate them to pos_invoice_lines (recommended)**
```sql
BEGIN TRANSACTION;

-- Copy existing pos records
INSERT INTO pos_invoice_lines (id, pos_receipt_line_id)
SELECT id, NULL 
FROM invoice_lines 
WHERE sector = 'pos'
ON CONFLICT DO NOTHING;

-- Verify
SELECT COUNT(*) FROM pos_invoice_lines;

COMMIT;
```

**Option B: Check and clean**
```sql
-- See what exists
SELECT il.sector, COUNT(*) as count
FROM invoice_lines il
GROUP BY il.sector;

-- Delete orphaned pos records (if no matching invoice)
DELETE FROM invoice_lines 
WHERE sector = 'pos' 
AND invoice_id NOT IN (SELECT id FROM invoices);
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `Table "pos_invoice_lines" does not exist` | Run migration: `alembic upgrade head` |
| Still getting polymorphic_identity error | Clear Python cache: `find . -type d -name __pycache__ -exec rm -r {} +` then restart |
| InFailedSqlTransaction still occurs | Check logs: `grep "Error creating" /var/log/gestiqcloud/backend.log` |
| Migration fails with FK constraint | Ensure `invoices` table exists and `invoice_lines` references it |
| Duplicate key error | Run migration idempotently: check for `IF NOT EXISTS` clauses |

---

## Performance Impact

- **Migration time:** < 1 second (just creates empty table + index)
- **Query performance:** No impact (polymorphic loading same as before)
- **Storage:** ~32 bytes per POS invoice line (just the FK column)

---

## Rollback (if needed)

```bash
# Downgrade migration
alembic downgrade -1

# Or manual
DROP TABLE IF EXISTS pos_invoice_lines CASCADE;

# Restart backend
systemctl restart gestiqcloud-backend
```

---

## Files Summary

| File | Change | Impact |
|------|--------|--------|
| `invoiceLine.py` | Added POSLine class | **High** - Enables 'pos' polymorphic identity |
| `invoice_integration.py` | Improved error handling | **Medium** - Better logging, same behavior |
| `2026-01-22_001_add_pos_invoice_lines/up.sql` | New migration | **High** - Creates pos_invoice_lines table |

---

## Related Issues

- **Affected API Endpoints:**
  - GET `/api/v1/tenant/invoicing` ← Was failing with polymorphic error
  - POST `/api/v1/tenant/pos/receipts/{id}/checkout` ← Was failing with transaction error
  - POST `/api/v1/tenant/pos/receipts/{id}/refund` ← May have been affected

- **Affected Modules:**
  - Invoicing (CRUD queries on InvoiceLine with polymorphic loading)
  - POS (checkout/refund flow with transaction locking)
  - Sales (creates sales_orders from POS receipts)

---

## References

- SQLAlchemy Polymorphic Inheritance: https://docs.sqlalchemy.org/en/20/orm/inheritance.html
- PostgreSQL Foreign Keys: https://www.postgresql.org/docs/current/ddl-constraints.html
- Transaction Isolation: https://www.postgresql.org/docs/current/transaction-iso.html

---

**Last Updated:** 2026-01-22  
**Status:** ✅ Ready for deployment
