# Migration: Store Credits

## Purpose
Sistema completo de vales/créditos de tienda para:
- Devoluciones sin efectivo
- Promociones y cupones
- Saldo reutilizable

## Features
- ✅ Código único generado automáticamente (SC-XXXXXX)
- ✅ Múltiples redenciones (hasta agotar saldo)
- ✅ Caducidad configurable
- ✅ Auditoría completa de eventos
- ✅ RLS tenant isolation

## Tables
1. **store_credits**: Vales activos con saldo
2. **store_credit_events**: Historial de emisión/redención

## Testing
```sql
-- Crear vale de prueba
INSERT INTO store_credits (tenant_id, code, currency, amount_initial, amount_remaining)
VALUES (
  (SELECT id FROM tenants LIMIT 1),
  generate_store_credit_code(),
  'EUR',
  50.00,
  50.00
);

-- Ver vales activos
SELECT code, amount_remaining, status FROM store_credits WHERE status = 'active';
```
