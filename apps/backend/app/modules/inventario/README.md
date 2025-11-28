# Módulo: inventario

Propósito: stock, movimientos y alertas.

## Endpoints
- Tenant: `interface/http/tenant.py` prefix `/inventory`.

## Componentes clave
- `application/use_cases.py`, `ports.py`, `dto.py`: lógica de inventario y movimientos.
- `infrastructure/repositories.py`: persistencia de stock y movimientos.
- `interface/http/schemas.py`: schemas de request/response.

## Notas
- Se integra con sales/pos/purchases/production para ajustar stock.
- Considerar locks/transacciones para movimientos concurrentes.
