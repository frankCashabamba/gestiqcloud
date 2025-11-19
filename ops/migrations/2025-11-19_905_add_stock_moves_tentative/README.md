# Migration: 2025-11-19_905_add_stock_moves_tentative

## Description
Adds `tentative` boolean field to `stock_moves` table to mark provisional inventory movements.

## Tables Modified
- `stock_moves`: Added `tentative` (BOOLEAN, NOT NULL, default FALSE)

## Testing
```sql
SELECT COUNT(*) FROM stock_moves WHERE tentative = TRUE;
```
