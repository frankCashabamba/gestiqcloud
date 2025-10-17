# RLS Implementation Summary — Imports Module

**Date**: 2025-10-17  
**Module**: Imports  
**Spec**: SPEC-1 (Row-Level Security + Tenant Middleware)

## ✅ Completed Tasks

### 1. Migration Files Created

**Location**: `ops/migrations/2025-10-17_051_imports_rls_policies/`

- ✅ **up.sql** — 7 tables, 28 policies (4 per table: SELECT/INSERT/UPDATE/DELETE)
- ✅ **down.sql** — Rollback script (disables RLS)
- ✅ **README.md** — Technical documentation
- ✅ **APPLY.md** — Step-by-step deployment guide

**Tables covered**:
- `import_batches`
- `import_items`
- `import_mappings`
- `import_item_corrections`
- `import_lineage`
- `import_attachments`
- `import_ocr_jobs`

**Policy naming**: `p_{table}_tenant_{action}`  
**GUC variable**: `app.tenant_id` (UUID, `SET LOCAL`)

### 2. Tenant Middleware

**File**: `apps/backend/app/modules/imports/infrastructure/tenant_middleware.py`

**Functions**:
- `set_tenant_context(session, tenant_id)` — Sets `app.tenant_id` GUC
- `@with_tenant_context` — Decorator for repository methods
- `require_tenant_context(db)` — Validation for critical operations

**Features**:
- ✅ Raises `ValueError` if `tenant_id` is None
- ✅ Logs warnings for debugging
- ✅ Stores `tenant_id` in `session.info` for utilities
- ✅ Compatible with `SET LOCAL` (transaction-scoped)

### 3. Repository Updates

**File**: `apps/backend/app/modules/imports/infrastructure/repositories.py`

**Changes**:
- ✅ All methods now accept `tenant_id: uuid.UUID` as first parameter
- ✅ Removed `WHERE empresa_id = ...` filters (RLS handles it)
- ✅ Added `@with_tenant_context` decorator to all methods
- ✅ Simplified queries (no manual tenant filtering)

**Methods updated**:
- `get_batch(db, tenant_id, batch_id)`
- `list_batches(db, tenant_id, status=None)`
- `list_items(db, tenant_id, batch_id, ...)`
- `bulk_add_items(db, tenant_id, batch_id, items)`
- `exists_promoted_hash(db, tenant_id, dedupe_hash)`

### 4. Test Suite

**File**: `apps/backend/tests/modules/imports/test_rls_isolation.py`

**Test classes**:

#### `TestRLSIsolation` (PostgreSQL only, requires `--rls` flag)
- ✅ `test_tenant_a_cannot_see_tenant_b_data` — Cross-tenant isolation
- ✅ `test_tenant_b_cannot_see_tenant_a_data` — Reverse isolation
- ✅ `test_insert_with_wrong_tenant_id_fails` — Policy violation
- ✅ `test_queries_without_tenant_context_return_zero_rows` — Fail-safe
- ✅ `test_switching_tenant_context_changes_visible_data` — Context switching

#### `TestMiddlewareValidation` (SQLite-compatible)
- ✅ `test_set_tenant_context_raises_on_none` — Validation
- ✅ `test_decorator_warns_when_tenant_id_none` — Logging

**Fixtures**:
- `tenant_a_id`, `tenant_b_id` — UUID fixtures
- `setup_test_data` — Creates test batches for both tenants

### 5. Verification Script

**File**: `ops/scripts/verify_rls_imports.py`

**Features**:
- ✅ Checks RLS is ENABLED on all tables
- ✅ Verifies FORCE RLS is active (no superuser bypass)
- ✅ Validates CRUD policies exist (SELECT/INSERT/UPDATE/DELETE)
- ✅ Runs live isolation tests (`--test-isolation` flag)
- ✅ Generates summary report with ✓/✗ symbols

**Usage**:
```bash
# Basic check
python ops/scripts/verify_rls_imports.py

# With isolation tests
python ops/scripts/verify_rls_imports.py --test-isolation
```

## 📊 Policy Summary

| Table                       | Policies | RLS     | FORCE |
|-----------------------------|----------|---------|-------|
| import_batches              | 4        | ✓       | ✓     |
| import_items                | 4        | ✓       | ✓     |
| import_mappings             | 4        | ✓       | ✓     |
| import_item_corrections     | 4        | ✓       | ✓     |
| import_lineage              | 4        | ✓       | ✓     |
| import_attachments          | 4        | ✓       | ✓     |
| import_ocr_jobs             | 4        | ✓       | ✓     |
| **Total**                   | **28**   | **7/7** | **7/7** |

## 🔒 Security Guarantees

1. **Tenant isolation**: Queries filtered by `tenant_id` at DB level
2. **No bypass**: `FORCE RLS` prevents superuser access without GUC
3. **Fail-safe**: Missing `app.tenant_id` → 0 rows returned
4. **Audit trail**: All context changes logged via middleware
5. **Cross-tenant protection**: INSERT/UPDATE with wrong `tenant_id` → policy violation

## 📁 Files Created/Modified

### Created (9 files)
1. `ops/migrations/2025-10-17_051_imports_rls_policies/up.sql`
2. `ops/migrations/2025-10-17_051_imports_rls_policies/down.sql`
3. `ops/migrations/2025-10-17_051_imports_rls_policies/README.md`
4. `ops/migrations/2025-10-17_051_imports_rls_policies/APPLY.md`
5. `apps/backend/app/modules/imports/infrastructure/tenant_middleware.py`
6. `apps/backend/tests/modules/imports/test_rls_isolation.py`
7. `ops/scripts/verify_rls_imports.py`
8. `RLS_IMPLEMENTATION_SUMMARY.md` (this file)

### Modified (1 file)
1. `apps/backend/app/modules/imports/infrastructure/repositories.py`
   - Signature changes: `empresa_id: int` → `tenant_id: uuid.UUID`
   - Removed manual `WHERE empresa_id` filters
   - Added `@with_tenant_context` decorators

## 🚀 Deployment Steps

### 1. Apply Migration
```bash
export DATABASE_URL="postgresql://user:pass@host/db"
psql "$DATABASE_URL" -f ops/migrations/2025-10-17_051_imports_rls_policies/up.sql
```

### 2. Verify RLS
```bash
python ops/scripts/verify_rls_imports.py --test-isolation
```

### 3. Run Tests
```bash
# Unit tests (SQLite)
pytest apps/backend/tests/modules/imports/test_rls_isolation.py -k unit -v

# RLS tests (PostgreSQL)
pytest apps/backend/tests/modules/imports/test_rls_isolation.py --rls -v
```

### 4. Update API Code
- Add `tenant_id: uuid.UUID = Depends(get_tenant_id)` to all endpoints
- Replace `empresa_id` with `tenant_id` in repository calls
- Test integration endpoints with tenant context

## ⚠️ Breaking Changes

### Repository Method Signatures

**Before**:
```python
repo.get_batch(db, empresa_id=1, batch_id=123)
repo.list_batches(db, empresa_id=1, status="PENDING")
repo.bulk_add_items(db, empresa_id=1, batch_id=123, items=[...])
```

**After**:
```python
repo.get_batch(db, tenant_id=uuid.UUID(...), batch_id=123)
repo.list_batches(db, tenant_id=uuid.UUID(...), status="PENDING")
repo.bulk_add_items(db, tenant_id=uuid.UUID(...), batch_id=123, items=[...])
```

### API Endpoints

**Before**:
```python
@router.get("/batches")
def list_batches(
    empresa_id: int = Depends(get_empresa_id),
    db: Session = Depends(get_db),
):
    return repo.list_batches(db, empresa_id)
```

**After**:
```python
@router.get("/batches")
def list_batches(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    return repo.list_batches(db, tenant_id)
```

## 🧪 Test Results (Expected)

### Unit Tests
```
test_set_tenant_context_raises_on_none ................ PASSED
test_decorator_warns_when_tenant_id_none .............. PASSED
```

### RLS Integration Tests (PostgreSQL)
```
test_tenant_a_cannot_see_tenant_b_data ................ PASSED
test_tenant_b_cannot_see_tenant_a_data ................ PASSED
test_insert_with_wrong_tenant_id_fails ................ PASSED
test_queries_without_tenant_context_return_zero_rows .. PASSED
test_switching_tenant_context_changes_visible_data .... PASSED
```

### Verification Script
```
RLS Verification for Imports Module
====================================

1. Checking RLS is enabled...
  ✓ import_batches: FORCE
  ✓ import_items: FORCE
  ✓ import_mappings: FORCE
  ✓ import_item_corrections: FORCE
  ✓ import_lineage: FORCE
  ✓ import_attachments: FORCE
  ✓ import_ocr_jobs: FORCE
  ✓ All tables have RLS ENABLED and FORCE

2. Checking CRUD policies...
  ✓ import_batches: 4 policies
  ✓ import_items: 4 policies
  ✓ import_mappings: 4 policies
  ✓ import_item_corrections: 4 policies
  ✓ import_lineage: 4 policies
  ✓ import_attachments: 4 policies
  ✓ import_ocr_jobs: 4 policies
  ✓ All tables have full CRUD policies

3. Testing tenant isolation...
  ✓ Isolation tests passed

====================================
✓ ALL CHECKS PASSED
```

## 📝 Next Steps

1. **Apply to other modules**:
   - Catalog (products, categories)
   - Sales (orders, invoices)
   - Inventory (warehouses, stock)
   - POS (registers, shifts)

2. **Cleanup legacy code**:
   - Remove `empresa_id` filters after 2 releases
   - Deprecate `empresa_id` column (keep for 1-2 months)

3. **Monitoring**:
   - Add metrics for RLS policy hits
   - Alert on "tenant_id is None" warnings
   - Track query performance impact

4. **Documentation**:
   - Update API docs with tenant_id requirement
   - Add RLS section to developer guide
   - Create troubleshooting runbook

## 🔗 References

- **AGENTS.md**: M1 — Tenancy UUID + RLS
- **PostgreSQL RLS Docs**: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- **Base RLS**: `apps/backend/app/db/rls.py`
- **Example Policies**: `apps/backend/app/db/rls_policies.sql`

---

**Status**: ✅ **READY FOR REVIEW**  
**Next Action**: Apply migration to staging DB and run verification
