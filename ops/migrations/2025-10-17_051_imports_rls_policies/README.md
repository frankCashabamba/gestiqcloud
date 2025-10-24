# Migration: Imports Module RLS Policies

**Date**: 2025-10-17  
**Module**: Imports  
**Type**: Security (Row-Level Security)

## Summary

Enables PostgreSQL Row-Level Security (RLS) for all imports module tables to enforce tenant isolation at the database level.

## Tables Affected

- `import_batches`
- `import_items`
- `import_mappings`
- `import_item_corrections`
- `import_lineage`
- `import_attachments`
- `import_ocr_jobs`

## Policy Naming Convention

**Format**: `p_{table}_tenant_{action}`

Examples:
- `p_import_batches_tenant_select`
- `p_import_items_tenant_insert`
- `p_import_mappings_tenant_update`

## GUC Variable

**Name**: `app.tenant_id`  
**Type**: UUID  
**Scope**: `SET LOCAL` (transaction-scoped)

## Policy Logic

All policies enforce:
```sql
tenant_id = current_setting('app.tenant_id', true)::uuid
```

- **SELECT/UPDATE/DELETE**: `USING` clause filters visible rows
- **INSERT**: `WITH CHECK` validates new rows
- **UPDATE**: Both `USING` and `WITH CHECK` (prevents changing tenant_id)

## Application Changes Required

### 1. Repository Methods

All repository methods now require `tenant_id: uuid.UUID` as first parameter:

```python
# Before
repo.get_batch(db, empresa_id=1, batch_id=123)

# After
repo.get_batch(db, tenant_id=uuid.UUID(...), batch_id=123)
```

### 2. Middleware Usage

Import and use `@with_tenant_context` decorator:

```python
from app.modules.imports.infrastructure.tenant_middleware import with_tenant_context

class MyRepository:
    @with_tenant_context
    def get_data(self, db: Session, tenant_id: uuid.UUID, ...):
        # RLS context automatically set
        return db.query(...)
```

### 3. Manual Context Setting

For custom queries:

```python
from app.modules.imports.infrastructure.tenant_middleware import set_tenant_context

set_tenant_context(session, tenant_id)
result = session.execute(text("SELECT ..."))
```

## Testing

### Unit Tests (SQLite-compatible)

```bash
pytest apps/backend/tests/modules/imports/test_rls_isolation.py -k unit
```

### RLS Integration Tests (PostgreSQL only)

```bash
pytest apps/backend/tests/modules/imports/test_rls_isolation.py --rls
```

### Verification Script

```bash
python ops/scripts/verify_rls_imports.py --test-isolation
```

## Rollback

```bash
psql $DATABASE_URL -f ops/migrations/2025-10-17_051_imports_rls_policies/down.sql
```

**Warning**: Rollback disables tenant isolation. Ensure no multi-tenant queries are active.

## Security Considerations

1. **FORCE RLS**: Applied to prevent superuser bypass
2. **Fail-safe**: Queries without `app.tenant_id` return 0 rows
3. **Logging**: Middleware logs warnings when tenant_id is None
4. **Audit**: All tenant context changes are traceable via query logs

## Performance Impact

- **Minimal**: RLS policies use indexed `tenant_id` column
- **No additional queries**: Filtering happens at PostgreSQL level
- **Same query plan**: `tenant_id` filter added to existing WHERE clauses

## Related Files

- Migration: `ops/migrations/2025-10-17_051_imports_rls_policies/up.sql`
- Middleware: `apps/backend/app/modules/imports/infrastructure/tenant_middleware.py`
- Repository: `apps/backend/app/modules/imports/infrastructure/repositories.py`
- Tests: `apps/backend/tests/modules/imports/test_rls_isolation.py`
- Verification: `ops/scripts/verify_rls_imports.py`

## References

- AGENTS.md: M1 — Tenancy UUID + RLS
- PostgreSQL RLS Docs: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
