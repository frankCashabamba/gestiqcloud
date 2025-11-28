# Módulo: suppliers

Propósito: proveedores y contactos asociados.

## Endpoints
- Tenant: `interface/http/tenant.py` prefix `/suppliers`.

## Componentes clave
- `application/use_cases.py`, `ports.py`, `dto.py`: lógica de proveedores.
- `infrastructure/repositories.py`: persistencia.
- `interface/http/schemas.py`: schemas de request/response.

## Notas
- Conecta con compras y finanzas para pagos y conciliación.
