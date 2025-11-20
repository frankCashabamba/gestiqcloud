# Migration: 2025-11-20_907_align_schema_with_models

## Purpose
Align the database schema with SQLAlchemy models to fix test failures on GitHub Actions.

## Changes
1. **sales table**: Rename columns from English to Spanish to match `venta.py` model
   - `customer_id` → `cliente_id`
   - `sale_date` → `fecha`
   - `tax` → `taxes`
   - Add missing: `notas`, `usuario_id`, `estado`
   - Make `cliente_id` nullable

2. **business_types table**: Add NOT NULL constraint to `tenant_id`

3. **import_items table**: Fix unique index for ON CONFLICT idempotency

4. **stock_moves table**: Ensure warehouse_id FK is correct

5. **company_users table**: Fix id column to be UUID instead of integer

## Error Context
GitHub Actions tests were failing with:
- `FAILED test_ventas_repo_crud_compat - column "notas" does not exist`
- `FAILED test_imports_batches - ON CONFLICT constraint missing`
- `FAILED test_admin_config_tipo_empresa_crud - NULL in business_types.tenant_id`
- `FAILED test_smoke_pos_post - foreign key violation on warehouses`
