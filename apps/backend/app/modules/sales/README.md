# Módulo: sales

Propósito: ventas/ordenes y flujos relacionados.

## Endpoints
- Tenant: `interface/http/tenant.py` prefixes `/sales_orders` y `/deliveries`.
- Conversions: `interface/http/conversions.py` prefix `/sales_orders`.

## Componentes clave
- `application/use_cases.py`: casos de uso de ventas.
- `application/dto.py` y `ports.py`: DTOs y puertos.
- `infrastructure/repositories.py`: persistencia.
- `interface/http/schemas.py`: schemas de request/response.

## Notas
- Integra con POS, inventory y payments para stocks y cobros.
- Respetar `tenant_id` y permisos; considerar RLS si se habilita.
