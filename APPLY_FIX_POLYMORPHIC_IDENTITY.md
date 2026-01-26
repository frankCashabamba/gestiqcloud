# Quick Start: Apply Polymorphic Identity 'pos' Fix

## What was fixed

1. ✅ Added `POSLine` model to support `polymorphic_identity='pos'` in `invoice_lines`
2. ✅ Created migration to add `pos_invoice_lines` table
3. ✅ Improved error handling in `invoice_integration.py` for transaction failures

## Files Modified

```
✓ apps/backend/app/models/core/invoiceLine.py
  - Added POSLine class (lines 68-85)

✓ apps/backend/app/modules/pos/application/invoice_integration.py
  - Improved exception handling in create_invoice_from_receipt
  - Improved exception handling in create_sale_from_receipt
  - Added savepoint documentation

✓ ops/migrations/2026-01-22_001_add_pos_invoice_lines/up.sql (NEW)
  - Creates pos_invoice_lines table
```

## Step-by-Step Installation

### 1. Pull Latest Changes
```bash
git pull origin main
```

### 2. Run Database Migration
```bash
# Option A: Using alembic
alembic upgrade head

# Option B: Using custom migration runner (if available)
python -m ops.migrations run

# Option C: Manual SQL (if needed)
# cd ops/migrations/2026-01-22_001_add_pos_invoice_lines
# psql -U user -d gestiqcloud < up.sql
```

### 3. Verify Migration Success
```sql
-- Check if table was created
\dt pos_invoice_lines

-- Check that invoices table can be queried (should not throw polymorphic_identity error)
SELECT COUNT(*) FROM invoices;

-- Check invoice_lines sectors
SELECT DISTINCT sector FROM invoice_lines;
```

### 4. Restart Backend Service
```bash
# If running locally
python -m uvicorn app.main:app --reload

# If running with systemd
systemctl restart gestiqcloud-backend

# If running with Docker
docker-compose restart backend
```

### 5. Test the Fix

**Test 1: Fetch Invoices (should not throw polymorphic_identity error)**
```bash
curl -X GET http://localhost:8000/api/v1/tenant/invoicing \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

**Test 2: Create a POS Receipt and Checkout**
```bash
# This should now work without InFailedSqlTransaction errors
curl -X POST http://localhost:8000/api/v1/tenant/pos/receipts/{receipt_id}/checkout \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

**Test 3: Check Logs**
```bash
# Should NOT see "No such polymorphic_identity 'pos' is defined"
tail -f /var/log/gestiqcloud/backend.log

# Should NOT see "InFailedSqlTransaction" errors (or at least they should be caught and logged cleanly)
```

## Handle Existing Data

### If you have 'pos' records in invoice_lines

**Option 1: Migrate them to pos_invoice_lines**
```sql
BEGIN;

-- Move existing 'pos' records to pos_invoice_lines
INSERT INTO pos_invoice_lines (id, pos_receipt_line_id)
SELECT id, NULL
FROM invoice_lines
WHERE sector = 'pos';

-- Verify
SELECT COUNT(*) FROM pos_invoice_lines;

COMMIT;
```

**Option 2: Delete invalid 'pos' records (if orphaned)**
```sql
-- Delete if no matching invoice exists
DELETE FROM invoice_lines
WHERE sector = 'pos'
AND invoice_id NOT IN (SELECT id FROM invoices);
```

**Option 3: Check what data exists**
```sql
-- See which sectors are actually in use
SELECT sector, COUNT(*) as count
FROM invoice_lines
GROUP BY sector
ORDER BY count DESC;

-- See if pos records have valid invoices
SELECT il.id, il.sector, il.invoice_id, i.number
FROM invoice_lines il
LEFT JOIN invoices i ON il.invoice_id = i.id
WHERE il.sector = 'pos';
```

## Troubleshooting

### Error: "pos_invoice_lines" table does not exist
**Solution:** Run the migration again
```bash
alembic upgrade head
```

### Error: Still getting "No such polymorphic_identity 'pos'"
**Solution:** Verify POSLine is imported in your models initialization
```bash
# Check that app/models/__init__.py imports invoiceLine module
grep -r "invoiceLine\|POSLine" apps/backend/app/models/__init__.py
```

### Error: InFailedSqlTransaction still occurs
**Solution:** This now logs better. Check logs for the actual underlying error:
```bash
tail -100 /var/log/gestiqcloud/backend.log | grep -A 5 "Error creating.*receipt"
```

### Transaction Timeout with FOR UPDATE
**Root cause:** The `FOR UPDATE` lock in `create_sale_from_receipt` waits for row locks
**Solution:** The improved error handling now catches and logs these cleanly. Monitor concurrency:
```bash
# Check for long-running transactions
psql -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"
```

## Verification Checklist

- [ ] Migration runs successfully
- [ ] `pos_invoice_lines` table exists
- [ ] No "polymorphic_identity 'pos'" errors in logs
- [ ] Can fetch invoices via API
- [ ] Can create POS receipts and checkout
- [ ] Existing data migrated or cleaned up

## Need Help?

Check the detailed documentation:
- `FIX_POLYMORPHIC_IDENTITY_POS.md` - Technical details
- `POS_INVOICING_FLOW.md` - POS integration architecture

## Rollback (if needed)

If something goes wrong, rollback the migration:
```bash
alembic downgrade -1
```

Or manually drop the table:
```sql
DROP TABLE IF EXISTS pos_invoice_lines CASCADE;
```

Then restart the backend.
