# Migration: 2025-11-19_904_add_sales_cliente_id

## Description
Adds `cliente_id` foreign key field to `sales` table.

## Tables Modified
- `sales`: Added `cliente_id` (UUID, nullable, FK to clients.id)

## Testing
```sql
SELECT COUNT(*) FROM sales WHERE cliente_id IS NOT NULL;
```
