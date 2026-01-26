# Fix for Polymorphic Identity 'pos' Error

## Problem Summary

You're getting two related errors:

### Error 1: InFailedSqlTransaction (Transaction Aborted)
```
transacción abortada, las órdenes serán ignoradas hasta el fin de bloque de transacción
```
This occurs when trying to create a sale from a POS receipt because a previous database operation failed and the transaction wasn't properly cleaned up.

### Error 2: No such polymorphic_identity 'pos' is defined
```
AssertionError: No such polymorphic_identity 'pos' is defined
```
This occurs when fetching invoices because the database contains `invoice_lines` records with `sector='pos'`, but the SQLAlchemy models only define `'bakery'` and `'workshop'` as valid polymorphic identities.

## Root Cause

The `invoice_lines` table uses a `sector` column as a polymorphic discriminator in SQLAlchemy. However:

1. **Python models** define only two polymorphic identities:
   - `'bakery'` → `BakeryLine` model
   - `'workshop'` → `WorkshopLine` model

2. **Database** contains records with `sector='pos'`, but there's no corresponding:
   - `POSLine` SQLAlchemy model
   - `pos_invoice_lines` table (for joined table inheritance)

## Solution

### Step 1: Add POSLine Model

Already done! The file `apps/backend/app/models/core/invoiceLine.py` now includes:

```python
class POSLine(InvoiceLine):
    """POS-generated line item model."""

    __tablename__ = "pos_invoice_lines"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("invoice_lines.id"), primary_key=True
    )
    pos_receipt_line_id: Mapped[UUID | None] = mapped_column(
        "pos_receipt_line_id", PGUUID(as_uuid=True), nullable=True
    )

    __mapper_args__ = {"polymorphic_identity": "pos"}
```

### Step 2: Run Migration

A migration has been created at:
```
ops/migrations/2026-01-22_001_add_pos_invoice_lines/up.sql
```

This creates the `pos_invoice_lines` table. Run migrations:

```bash
alembic upgrade head
# or if using custom migration runner:
python -m ops.migrations run
```

### Step 3: Handle Existing 'pos' Records

If you have existing `invoice_lines` with `sector='pos'`:

**Option A: If they're from invalid data import** 
- Delete them (they're orphaned if there's no matching invoice_id)
```sql
DELETE FROM invoice_lines WHERE sector = 'pos' AND invoice_id NOT IN (
    SELECT id FROM invoices
);
```

**Option B: If they're real data to migrate**
- Create corresponding `pos_invoice_lines` entries:
```sql
INSERT INTO pos_invoice_lines (id, pos_receipt_line_id)
SELECT id, NULL FROM invoice_lines WHERE sector = 'pos';
```

### Step 4: Fix Transaction Handling (Optional Enhancement)

The `create_sale_from_receipt` method in `apps/backend/app/modules/pos/application/invoice_integration.py` could be improved with better transaction isolation:

```python
def create_sale_from_receipt(self, receipt_id: UUID) -> dict | None:
    # ... existing checks ...
    
    try:
        # Start a savepoint to isolate this operation
        # If it fails, we can rollback without affecting other operations
        with self.db.begin_nested():
            # existing code ...
    except Exception as e:
        self.db.rollback()  # Ensure clean rollback
        logger.exception("Error creating sale from receipt: %s", e)
        return None
```

## Verification

After applying the migration, verify the fix:

1. **Check POSLine is recognized:**
   ```python
   from app.models.core.invoiceLine import POSLine
   print(POSLine.__mapper_args__)  # Should show polymorphic_identity: 'pos'
   ```

2. **Fetch invoices with POS lines:**
   ```bash
   curl -X GET http://localhost:8000/api/v1/tenant/invoicing \
     -H "Authorization: Bearer <token>"
   ```

3. **Check database:**
   ```sql
   SELECT COUNT(*), sector FROM invoice_lines GROUP BY sector;
   -- Should show results for 'bakery', 'workshop', 'pos', etc.
   ```

## Timeline

- **Migration Created:** 2026-01-22
- **Files Modified:** 
  - `apps/backend/app/models/core/invoiceLine.py` (added POSLine)
  - `ops/migrations/2026-01-22_001_add_pos_invoice_lines/up.sql` (new)

## Additional Notes

The polymorphic inheritance pattern in SQLAlchemy requires:
1. Base table with discriminator column: `invoice_lines` (sector)
2. Base model class: `InvoiceLine`
3. Subclass tables (one per polymorphic identity): `bakery_lines`, `workshop_lines`, `pos_invoice_lines`
4. Subclass models with matching `polymorphic_identity`: `BakeryLine`, `WorkshopLine`, `POSLine`

The new `pos_invoice_lines` table inherits from `invoice_lines` via foreign key `id REFERENCES invoice_lines(id)`.
