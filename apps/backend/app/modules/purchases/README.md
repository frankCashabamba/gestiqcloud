# Módulo: purchases

Propósito: compras y líneas de compra.

## Endpoints
- Tenant: `interface/http/tenant.py` prefix `/purchases`.

## Componentes clave
- `application/use_cases.py`, `ports.py`, `dto.py`: lógica y contratos.
- `infrastructure/repositories.py`: persistencia.
- `interface/http/schemas.py`: schemas de request/response.

## Notas
- Integra con inventario para recepciones/stock y contabilidad para asientos.
