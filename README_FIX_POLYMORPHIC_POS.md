# Fix for "No such polymorphic_identity 'pos'" and InFailedSqlTransaction Errors

## Quick Links

1. **For Immediate Deploy:** [APPLY_FIX_POLYMORPHIC_IDENTITY.md](./APPLY_FIX_POLYMORPHIC_IDENTITY.md)
   - Step-by-step installation guide
   - Migration commands
   - Testing procedures
   - Troubleshooting

2. **For Understanding the Issue:** [SOLUTION_POLYMORPHIC_IDENTITY_ERROR.md](./SOLUTION_POLYMORPHIC_IDENTITY_ERROR.md)
   - Complete technical explanation
   - Error analysis
   - Architecture details
   - Data migration options

3. **For Technical Deep Dive:** [FIX_POLYMORPHIC_IDENTITY_POS.md](./FIX_POLYMORPHIC_IDENTITY_POS.md)
   - Root cause analysis
   - Solution details
   - Code examples
   - References

---

## Problem in 30 Seconds

**Error 1:** `AssertionError: No such polymorphic_identity 'pos' is defined`
- The database has `invoice_lines` records with `sector='pos'`
- SQLAlchemy models don't have a `POSLine` class to handle 'pos'

**Error 2:** `InFailedSqlTransaction: transacción abortada...`
- Transaction fails due to polymorphic loading errors
- Can cascade to other failed transactions

---

## Solution Summary

| Component | Change | Status |
|-----------|--------|--------|
| POSLine Model | Added to `invoiceLine.py` | ✅ Complete |
| Database Table | Created `pos_invoice_lines` via migration | ✅ Complete |
| Error Handling | Improved in `invoice_integration.py` | ✅ Complete |

---

## What You Need to Do

### 1. Update Code (automatic via git pull)
```bash
git pull origin main
```

### 2. Run Migration
```bash
alembic upgrade head
```

### 3. Restart Backend
```bash
systemctl restart gestiqcloud-backend
```

### 4. Verify
```bash
# Test API - should no longer throw polymorphic_identity error
curl -X GET http://localhost:8000/api/v1/tenant/invoicing \
  -H "Authorization: Bearer $TOKEN"
```

---

## Changed Files

```
✓ apps/backend/app/models/core/invoiceLine.py
  └─ Added POSLine class (lines 68-80)

✓ apps/backend/app/modules/pos/application/invoice_integration.py
  └─ Improved error handling in 2 methods

✓ ops/migrations/2026-01-22_001_add_pos_invoice_lines/ (NEW)
  └─ Creates pos_invoice_lines table
```

---

## Testing Checklist

- [ ] Migration runs without errors
- [ ] `pos_invoice_lines` table created
- [ ] Backend restarts successfully
- [ ] Can fetch invoices without polymorphic_identity error
- [ ] Can create POS receipts and checkout
- [ ] No InFailedSqlTransaction errors in logs

---

## Support

**Need help?**

1. Check [APPLY_FIX_POLYMORPHIC_IDENTITY.md](./APPLY_FIX_POLYMORPHIC_IDENTITY.md) troubleshooting section
2. Review logs: `tail -f /var/log/gestiqcloud/backend.log`
3. Check database: `psql -c "\dt pos_invoice_lines"`

**Rollback needed?**

```bash
alembic downgrade -1
systemctl restart gestiqcloud-backend
```

---

**Status:** ✅ Ready to Deploy
**Created:** 2026-01-22
**Impact:** High (fixes critical API errors)
**Risk:** Low (additive changes, backward compatible)
