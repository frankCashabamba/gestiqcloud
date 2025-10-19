# Migration: POS Invoicing Link

## Purpose
Conectar pos_receipts con invoices para conversión ticket→factura.

## Changes
- Añade `invoice_id` a `pos_receipts` (nullable)
- Añade `client_temp_id` para idempotencia offline
- Añade `metadata` JSONB para datos adicionales

## Dependencies
- Requiere tabla `invoices` existente
- Requiere tabla `pos_receipts` (de 2025-10-10_090_pos)

## Testing
```sql
-- Verificar estructura
\d pos_receipts;

-- Verificar índices
SELECT indexname FROM pg_indexes WHERE tablename = 'pos_receipts';
```
