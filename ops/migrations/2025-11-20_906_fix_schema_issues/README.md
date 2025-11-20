# Migration: 2025-11-20_906_fix_schema_issues

## Description
Fix schema issues discovered during test runs:

- Create missing unique index on `import_items(tenant_id, idempotency_key)` for ON CONFLICT support
- Add missing `taxes` column to `sales` table
- Resize `languages.code` from VARCHAR(10) to VARCHAR(50) to accommodate test data
- Ensure `sales.estado` has proper defaults

## Changes
- `import_items`: Add unique index for idempotency support
- `sales`: Add `taxes` column, ensure `estado` default
- `languages`: Expand `code` column size

## Test Coverage
Related tests:
- `test_imports_*.py` - Now have unique constraint for ON CONFLICT
- `test_admin_config_idioma_crud` - Larger code field for test data
- `test_repo_ventas_compat` - `taxes` column available
