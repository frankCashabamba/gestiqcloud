# Módulo: products

Propósito: catálogo de productos, categorías y precios.

## Endpoints
- Tenant: `interface/http/tenant.py` prefix `/products`.
- Admin: `interface/http/admin.py` prefix `/admin/products` (montado bajo `/api/v1`).
- Público: `interface/http/public.py` prefix `/products`.

## Componentes clave
- `application/use_cases.py`: lógica de productos (creación/edición/listado).
- `application/ports.py` y `dto.py`: interfaces y DTOs.
- `infrastructure/repositories.py`: acceso a DB.
- `interface/http/schemas.py`: Pydantic schemas de entrada/salida.

## Notas
- Integra con inventario y ventas/POS para stock y precios.
- Revisar permisos por rol/tenant al exponer endpoints.
