# Módulo: sales

Propósito: ventas/ordenes y flujos relacionados.

## Endpoints
- Tenant: `interface/http/tenant.py` prefixes `/sales_orders` y `/deliveries`.
- Conversions: `interface/http/conversions.py` prefix `/sales_orders`.

## Componentes clave
- Entidades principales: `sales_orders`, `sales_order_items`, `deliveries`.
- API tenant: `interface/http/tenant.py` y `interface/http/conversions.py`.

## Notas
- Integra con POS, inventory y payments para stocks y cobros.
- Respetar `tenant_id` y permisos; considerar RLS si se habilita.
