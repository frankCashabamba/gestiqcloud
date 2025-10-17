# How to Apply RLS for Imports Module

## Prerequisites

- [x] `tenant_id` column added to all imports tables (via previous migrations)
- [x] PostgreSQL 13+ database
- [x] Backup of database before applying

## Step-by-Step Application

### 1. Apply Migration

```bash
# Connect to database
export DATABASE_URL="postgresql://user:pass@host:port/db"

# Apply RLS policies
psql "$DATABASE_URL" -f ops/migrations/2025-10-17_051_imports_rls_policies/up.sql

# Verify (should show ENABLED/FORCE for all tables)
psql "$DATABASE_URL" -c "
SELECT tablename, rowsecurity
FROM pg_tables pt
JOIN pg_class pc ON pc.relname = pt.tablename
WHERE schemaname = 'public'
  AND tablename LIKE 'import_%'
"
```

### 2. Update Application Code

#### Update API Endpoints

**Before**:
```python
@router.get("/batches")
def list_batches(
    empresa_id: int = Depends(get_empresa_id),
    db: Session = Depends(get_db),
):
    repo = ImportsRepository()
    return repo.list_batches(db, empresa_id)
```

**After**:
```python
@router.get("/batches")
def list_batches(
    tenant_id: uuid.UUID = Depends(get_tenant_id),  # New
    db: Session = Depends(get_db),
):
    repo = ImportsRepository()
    return repo.list_batches(db, tenant_id)  # Pass tenant_id
```

#### Add Tenant ID Dependency

Create or update `apps/backend/app/modules/imports/interface/dependencies.py`:

```python
from uuid import UUID
from fastapi import Depends, Request
from app.db.rls import tenant_id_from_request

def get_tenant_id(request: Request) -> UUID:
    """Extract tenant_id from request."""
    tid = tenant_id_from_request(request)
    if not tid:
        raise HTTPException(status_code=401, detail="Tenant context required")
    return UUID(tid)
```

### 3. Update Tests

#### Fixture for Tenant Context

Add to `apps/backend/tests/conftest.py`:

```python
@pytest.fixture
def tenant_context(db: Session, test_tenant_id: uuid.UUID):
    """Set tenant context for tests."""
    from app.modules.imports.infrastructure.tenant_middleware import set_tenant_context
    set_tenant_context(db, test_tenant_id)
    yield test_tenant_id
    db.rollback()
```

#### Update Existing Tests

```python
# Before
def test_list_batches(db: Session):
    repo = ImportsRepository()
    batches = repo.list_batches(db, empresa_id=1)

# After
def test_list_batches(db: Session, tenant_context: uuid.UUID):
    repo = ImportsRepository()
    batches = repo.list_batches(db, tenant_context)
```

### 4. Run Verification

```bash
# Check RLS is enabled
python ops/scripts/verify_rls_imports.py

# Run isolation tests
python ops/scripts/verify_rls_imports.py --test-isolation

# Run unit tests
pytest apps/backend/tests/modules/imports/test_rls_isolation.py -k unit -v

# Run full RLS tests (PostgreSQL required)
pytest apps/backend/tests/modules/imports/test_rls_isolation.py --rls -v
```

### 5. Deploy Checklist

- [ ] Migration applied to staging DB
- [ ] Verification script passes
- [ ] RLS isolation tests pass
- [ ] Application code updated (all endpoints)
- [ ] Integration tests pass with new signatures
- [ ] Load tests confirm no performance regression
- [ ] Rollback plan tested in dev environment

## Common Issues

### Issue: "No rows returned"

**Cause**: `app.tenant_id` not set in session

**Fix**: Ensure `set_tenant_context()` called or `@with_tenant_context` used

```python
# Check current GUC
result = db.execute(text("SELECT current_setting('app.tenant_id', true)"))
print(result.scalar())  # Should print UUID, not empty string
```

### Issue: "Policy violation on INSERT"

**Cause**: `tenant_id` in data doesn't match GUC

**Fix**: Verify tenant_id passed to method matches session context:

```python
set_tenant_context(db, tenant_id)
batch = ImportBatch(tenant_id=tenant_id, ...)  # Must match!
db.add(batch)
```

### Issue: Tests fail with SQLite

**Cause**: RLS only works on PostgreSQL

**Fix**: Use pytest markers and conditional fixtures:

```python
@pytest.mark.skipif(
    "not config.getoption('--rls')",
    reason="RLS tests require PostgreSQL"
)
def test_rls_isolation(...):
    ...
```

## Rollback Procedure

```bash
# Disable RLS (emergency only)
psql "$DATABASE_URL" -f ops/migrations/2025-10-17_051_imports_rls_policies/down.sql

# Revert application code
git revert <commit-sha>

# Verify queries work without RLS
curl -H "Authorization: Bearer $TOKEN" \
     https://api.gestiqcloud.com/imports/batches
```

## Monitoring

After deployment, monitor:

1. **Error rate**: Should not increase (if it does, check tenant context)
2. **Query performance**: Should remain similar (RLS adds minimal overhead)
3. **Logs**: Watch for "tenant_id is None" warnings

```bash
# Check logs for RLS warnings
kubectl logs -l app=gestiqcloud-api --tail=100 | grep "tenant_id"

# Query slow log for RLS policies
psql "$DATABASE_URL" -c "
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
WHERE query LIKE '%import_%'
ORDER BY mean_exec_time DESC
LIMIT 10
"
```

## Next Steps

After successful deployment:

1. Apply RLS to other modules (catalog, sales, inventory)
2. Remove `empresa_id` filters from codebase (cleanup)
3. Add Copilot integration for RLS-aware queries
4. Implement audit logging for tenant context changes
